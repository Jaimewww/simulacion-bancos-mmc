"""C2 regression tests: replicated experiments, intervals and CLI artifacts."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.modelo.cliente import Nivel
from src.modelo.parametros import ParametrosEscenario, Unidad
from src.modelo.resultados import Disciplina
from src.modelo.motor_des import MotorDES, LlegadaPlaneada, generar_carga
from src.control.experimentos import (intervalo_confianza_95, ejecutar_replicas,
                                     ejecutar_matriz, agregar_replicas, validar_coherencia)

ROOT = Path(__file__).resolve().parents[1]


def escenario(**kw):
    valores = dict(nombre='prueba', unidad=Unidad.HORA, lam=1, mu=2, c=1,
                   p=0.5, origen_p='supuesto de prueba', horizon=10, warmup=2)
    return ParametrosEscenario(**(valores | kw))


def corrida():
    carga = tuple(LlegadaPlaneada(i, t, Nivel.GENERAL, s) for i, (t, s) in
                  enumerate(((0, 3), (1, 1), (2, 1), (3, 10), (4, 1))))
    return MotorDES(escenario(), Disciplina.FCFS, semilla=1, carga=carga).correr()


class ExperimentosTests(unittest.TestCase):
    def test_shared_inputs_between_disciplines(self):
        p = escenario(horizon=100, warmup=0)
        carga = generar_carga(p, 21)
        motores = [MotorDES(p, d, semilla=21, carga=carga) for d in Disciplina]
        self.assertEqual(motores[0].carga, motores[1].carga)
        self.assertEqual([(c.instante,c.nivel,c.duracion_servicio) for c in motores[0].carga],
                         [(c.instante,c.nivel,c.duracion_servicio) for c in motores[1].carga])
        a,b = [m.correr() for m in motores]
        self.assertEqual([(c.id_llegada,c.t_llegada,c.nivel) for c in a.clientes],
                         [(c.id_llegada,c.t_llegada,c.nivel) for c in b.clientes])
        # API uses exactly the same deterministic preassignment for each discipline.
        for m in motores:
            runs,_ = ejecutar_replicas(p,m.disciplina,1,21)
            self.assertEqual(runs[0].clientes,m.correr().clientes)


    def test_ic_zero_one_and_missing(self):
        for valores,n in (([],0),([None,float('nan')],0),([3],1)):
            ic = intervalo_confianza_95(valores)
            self.assertEqual(ic['n'], n)
            self.assertIsNone(ic['ic95_inf'])
            self.assertIsNone(ic['ic95_sup'])
            self.assertIn('insuficientes',ic['nota'])

    def test_student_known_quantile(self):
        ic = intervalo_confianza_95([1,2,3])
        self.assertEqual(ic['gl'],2)
        self.assertAlmostEqual(ic['ic95_sup'], 2+4.3026527299/(3**0.5),places=7)
        self.assertEqual(intervalo_confianza_95([2,2])['ic95_inf'],2)

    def test_validation_api(self):
        for replicas in (0,-1,True,1.5,'2',None):
            with self.subTest(replicas=replicas), self.assertRaisesRegex(ValueError,'repeticiones'):
                ejecutar_matriz(familias=(),repeticiones=replicas)
        for seed in (-1,True,0.5,'1',None):
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError,'semilla_base'):
                ejecutar_replicas(escenario(),Disciplina.FCFS,1,seed)

    def test_contraste_uses_aggregate(self):
        agg = agregar_replicas([corrida(),corrida()])
        reportes = validar_coherencia(agg,escenario())
        self.assertEqual(reportes[0]['observado'],2)
        self.assertFalse(reportes[0]['compatible_ic95'])
        self.assertAlmostEqual(reportes[0]['diferencia'],1.5)
        self.assertEqual(agg['Wq_pref']['n'],0)
        self.assertIsNone(validar_coherencia(agregar_replicas([corrida()]),escenario())[0]['compatible_ic95'])
        self.assertIsNone(validar_coherencia(agg,escenario(lam=2))[0]['ok'])

    def cli(self,*args):
        env = dict(os.environ)
        env.pop('PYTHONPATH',None)
        return subprocess.run([sys.executable,'main.py',*args],cwd=ROOT,env=env,capture_output=True,text=True)

    def test_imports_have_single_identity(self):
        import main
        from src.control import experimentos
        from src.modelo import resultados
        self.assertIs(main.Disciplina, resultados.Disciplina)
        self.assertIs(experimentos.Disciplina, resultados.Disciplina)
        self.assertNotIn('modelo.resultados', sys.modules)

    def test_both_families_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.cli('--familia','ambas','--replicas','1','--horizon','4',
                         '--warmup','1','--salida',tmp)
            self.assertEqual(r.returncode,0,r.stderr)
            rows = list(csv.DictReader((Path(tmp)/'resumen.csv').read_text(encoding='utf-8').splitlines()))
            self.assertEqual(len(rows),18)
            self.assertEqual({r['unidad'] for r in rows}, {'hora','minuto'})
            self.assertTrue(all(r['Lq_global_ic95_inf'] == '' for r in rows))
        self.assertEqual(self.cli('--help').returncode,0)

    def test_invalid_cli(self):
        for args in (('--replicas','0'),('--replicas','-2'),('--replicas','x'),
                     ('--semilla-base','-1'),('--semilla-base','x'),('--warmup','99','--horizon','1')):
            with self.subTest(args=args), tempfile.TemporaryDirectory() as tmp:
                r = self.cli(*args,'--salida',tmp)
                self.assertEqual(r.returncode,2,r.stderr)
                self.assertNotIn('Traceback',r.stderr)
                self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_cli_csv_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.cli('--familia','marhamah','--replicas','2','--horizon','20',
                         '--warmup','2','--p','0','--origen-p','supuesto prueba','--salida',tmp)
            self.assertEqual(r.returncode,0,r.stderr)
            replicas = list(csv.DictReader((Path(tmp)/'replicas.csv').read_text(encoding='utf-8').splitlines()))
            resumen = list(csv.DictReader((Path(tmp)/'resumen.csv').read_text(encoding='utf-8').splitlines()))
            self.assertEqual(len(replicas),16)
            self.assertEqual(len(resumen),8)
            for fila in replicas:
                self.assertEqual(fila['wq_pref_muestra'],'')
                self.assertEqual(fila['n_inicio_pref'],'0')
                self.assertEqual(fila['conservacion_ok'],'True')
                self.assertEqual(int(fila['pendientes']),int(fila['pendientes_en_cola'])+int(fila['pendientes_en_servicio']))
                self.assertEqual(len(json.loads(fila['little_json'])['comprobaciones_little']),3)
            for fila in resumen:
                self.assertEqual(fila['Wq_pref_n'],'0')
                self.assertEqual(fila['Wq_pref_ic95_inf'],'')
                self.assertEqual(fila['Lq_global_n'],'2')
                self.assertEqual(fila['unidad'],'minuto')
                self.assertEqual(len(json.loads(fila['coherencia_json'])),3)
            meta = json.loads((Path(tmp)/'metadata.json').read_text(encoding='utf-8'))
            for ds in meta['matriz'].values():
                self.assertEqual(ds['fcfs']['semillas'],ds['prioridad']['semillas'])
                self.assertEqual(len(ds['fcfs']['verificaciones_replicas']),2)

    def test_cli_reemplaza_solo_resultados_generados(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for nombre in ('replicas_20200101_000000.csv', 'resumen_20200101_000000.csv',
                           'metadata_20200101_000000.json'):
                (base/nombre).write_text('anterior', encoding='utf-8')
            (base/'notas.csv').write_text('conservar', encoding='utf-8')
            r = self.cli('--familia','marhamah','--replicas','1','--horizon','4',
                         '--warmup','1','--salida',tmp)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(sorted(p.name for p in base.iterdir()),
                             ['figuras','metadata.json','notas.csv','replicas.csv','resumen.csv'])
            self.assertEqual((base/'notas.csv').read_text(encoding='utf-8'),'conservar')


if __name__ == '__main__':
    unittest.main()
