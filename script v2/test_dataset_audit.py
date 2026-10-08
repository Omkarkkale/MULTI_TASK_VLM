"""Focused checks for audit identities, timestamp matching, and preview coverage."""
from pathlib import Path
from types import SimpleNamespace
import unittest

from audit_mcap_dataset import nearest, preview_indices, source_identity, stamp_ns


class AuditHelpersTest(unittest.TestCase):
    def test_night_suffix_preserves_recording_id(self):
        _, rec, uid = source_identity(Path("data/run_eye_37_night_mcaps.mcap"), Path("data"))
        self.assertEqual(rec, "37")
        self.assertTrue(uid.startswith("eye_37_"))
        self.assertNotEqual(uid, source_identity(Path("data/run_eye_38_night_mcaps.mcap"), Path("data"))[2])

    def test_same_id_in_different_source_paths_does_not_collide(self):
        a = source_identity(Path("data/week1/run_eye_37.mcap"), Path("data"))
        b = source_identity(Path("data/week2/run_eye_37.mcap"), Path("data"))
        self.assertEqual(a[1], b[1])
        self.assertNotEqual(a[2], b[2])

    def test_nearest_matches_brute_force_and_breaks_ties_earlier(self):
        rows = [{"timestamp_ns":t,"index":i} for i,t in enumerate([10,20,40,40,80])]
        times = [r["timestamp_ns"] for r in rows]
        for t in range(0,100):
            actual = nearest(t,rows,times)
            self.assertEqual(actual["timestamp_ns"],min(times,key=lambda x:(abs(x-t),x)))
        self.assertIsNone(nearest(10,[],[]))

    def test_preview_selection_covers_ends_without_duplicate_slots(self):
        self.assertEqual(preview_indices(0,8),set())
        self.assertEqual(preview_indices(3,8),{0,1,2})
        slots = preview_indices(2372,8)
        self.assertEqual(len(slots),8)
        self.assertIn(0,slots)
        self.assertIn(2371,slots)

    def test_ros_stamp_validation(self):
        def msg(sec,nano):
            return SimpleNamespace(header=SimpleNamespace(stamp=SimpleNamespace(sec=sec,nanosec=nano)))
        self.assertEqual(stamp_ns(msg(1,999999999)),1999999999)
        for sec,nano in [(0,0),(-1,0),(1,-1),(1,1000000000)]:
            with self.assertRaises(ValueError):
                stamp_ns(msg(sec,nano))


if __name__ == "__main__":
    unittest.main()
