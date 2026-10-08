"""Regresiones de aislamiento de diagnóstico y cierre del servidor local."""
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from messi.desktop import LocalServer, run_server
from messi.diagnostics import self_test
from messi.paths import database_path


class DesktopLifecycleTests(unittest.TestCase):
    def test_cancelled_start_never_launches_a_process(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"MESSI_DATA_DIR": directory}):
            server = LocalServer()
            server.close()
            with patch("messi.desktop.subprocess.Popen") as create_process:
                with self.assertRaisesRegex(RuntimeError, "cancelado"):
                    server.start()
                create_process.assert_not_called()
            self.assertIsNone(server.process)
            self.assertIsNone(server._log)

    def test_repeated_close_terminates_server_and_releases_log_once(self):
        server = LocalServer()
        process = Mock()
        process.poll.return_value = None
        process.terminate.side_effect = lambda: setattr(process.poll, "return_value", 0)
        server.process = process
        log = Mock()
        server._log = log
        server.close()
        server.close()
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=5)
        log.close.assert_called_once()
        self.assertIsNone(server._log)

    def test_closing_during_process_creation_leaves_no_running_child(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"MESSI_DATA_DIR": directory}):
            server = LocalServer()
            launching, release, closed = threading.Event(), threading.Event(), threading.Event()
            errors = []
            process = Mock()
            process.poll.return_value = None
            process.terminate.side_effect = lambda: setattr(process.poll, "return_value", 0)

            def create_process(*args, **kwargs):
                launching.set()
                if not release.wait(5):
                    raise RuntimeError("La prueba no liberó el arranque.")
                return process

            def start():
                try:
                    server.start()
                except RuntimeError as error:
                    errors.append(error)

            def close():
                server.close()
                closed.set()

            with patch("messi.desktop.subprocess.Popen", side_effect=create_process), \
                    patch("messi.windows_process.protect_process", return_value=None):
                starter = threading.Thread(target=start)
                starter.start()
                self.assertTrue(launching.wait(5))
                closer = threading.Thread(target=close)
                closer.start()
                self.assertTrue(server._stop.wait(5))
                self.assertFalse(closed.is_set())
                release.set()
                starter.join(5)
                closer.join(5)
                self.assertFalse(starter.is_alive())
                self.assertFalse(closer.is_alive())
            self.assertTrue(closed.is_set())
            self.assertEqual(process.poll(), 0)
            process.terminate.assert_called_once()
            self.assertTrue(errors)

    def test_invalid_port_is_rejected_before_importing_streamlit(self):
        for port in (0, 1023, 65536):
            with self.subTest(port=port), self.assertRaisesRegex(ValueError, "Puerto local"):
                run_server(port)


class DiagnosticIsolationTests(unittest.TestCase):
    def test_self_test_uses_temporary_directory_and_restores_existing_override(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "datos-del-usuario"
            observed = []

            def probe(temporary):
                observed.append(temporary)
                path = database_path()
                path.parent.mkdir(parents=True)
                path.write_bytes(b"prueba")
                # TMP puede usar un alias Windows 8.3; comparar rutas físicas.
                self.assertTrue(path.resolve().is_relative_to(temporary.resolve()))
                return {"ok": True}

            with patch.dict(os.environ, {"MESSI_DATA_DIR": str(original)}), \
                    patch("messi.diagnostics._self_test_in_temporary_directory", side_effect=probe):
                self.assertEqual(self_test(), {"ok": True})
                self.assertEqual(os.environ["MESSI_DATA_DIR"], str(original))
            self.assertFalse(original.exists())
            self.assertFalse(observed[0].exists())

    def test_failing_self_test_restores_absent_override_and_cleans_temporary_files(self):
        observed = []

        def probe(temporary):
            observed.append(temporary)
            raise RuntimeError("fallo de prueba")

        with patch.dict(os.environ):
            os.environ.pop("MESSI_DATA_DIR", None)
            with patch("messi.diagnostics._self_test_in_temporary_directory", side_effect=probe):
                with self.assertRaisesRegex(RuntimeError, "fallo de prueba"):
                    self_test()
            self.assertNotIn("MESSI_DATA_DIR", os.environ)
        self.assertFalse(observed[0].exists())


if __name__ == "__main__":
    unittest.main()
