"""Quick test script to verify all modules work and benchmark speed."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diskmapper.scanner.disk_scanner import DiskScanner
from diskmapper.analysis.criticality_engine import criticality_score, score_label, annotate_tree
from diskmapper.analysis.cleanup_engine import disk_overview, detect_hidden_space
from diskmapper.scanner.size_analyzer import largest_files, largest_folders, all_files, all_folders
from diskmapper.reports.exporter import export_csv

print("✅ All modules imported successfully")

# Disk overview
ov = disk_overview()
total_gb = ov["total"] / 1e9
used_gb = ov["used"] / 1e9
free_gb = ov["free"] / 1e9
pct = ov["percent_used"]
print(f"\n📊 Disk Overview")
print(f"   Drive:  {ov['drive']}")
print(f"   Total:  {total_gb:.1f} GB")
print(f"   Used:   {used_gb:.1f} GB ({pct}%)")
print(f"   Free:   {free_gb:.1f} GB")

# Criticality tests
tests = [
    r"C:\Windows",
    r"C:\Windows\System32",
    r"C:\Program Files",
    r"C:\Users",
    r"C:\Windows\Temp",
    r"C:\$Recycle.Bin",
]
print(f"\n🔒 Criticality Scores")
for p in tests:
    s = criticality_score(p)
    print(f"   {s:3d}  {score_label(s):30s}  {p}")

# Hidden space
print(f"\n🔍 Hidden Space Detection")
for h in detect_hidden_space():
    status = f"{h.measured_size / 1e6:.1f} MB" if h.accessible else "access denied"
    print(f"   {'✅' if h.accessible else '🔒'} {h.rule.description:30s}  {status}")

# ── Benchmark: Temp folder scan ──────────────────────────────────────
import tempfile
temp = tempfile.gettempdir()
print(f"\n⏱️  Benchmark: scanning {temp}")
print(f"   Workers: 16 threads, work-queue pattern (all depths parallel)")

t0 = time.perf_counter()
scanner = DiskScanner(temp, max_workers=16)
root = scanner.scan()
scan_time = time.perf_counter() - t0

print(f"   Scanned {scanner.scanned_files:,} files, {scanner.scanned_folders:,} folders")
print(f"   Total size: {root.total_size / 1e6:.1f} MB")
print(f"   Scan time:  {scan_time:.3f}s")

# Benchmark tree annotation
t0 = time.perf_counter()
annotate_tree(root)
ann_time = time.perf_counter() - t0
print(f"   Annotate:   {ann_time:.3f}s")

# Benchmark all_files / all_folders (iterative)
t0 = time.perf_counter()
af = all_files(root)
af_time = time.perf_counter() - t0
print(f"   all_files:  {af_time:.3f}s  ({len(af):,} files)")

t0 = time.perf_counter()
ad = all_folders(root)
ad_time = time.perf_counter() - t0
print(f"   all_folders:{ad_time:.3f}s  ({len(ad):,} folders)")

t0 = time.perf_counter()
lf = largest_files(root, 20)
lf_time = time.perf_counter() - t0
print(f"   top20 files:{lf_time:.3f}s")

t0 = time.perf_counter()
ld = largest_folders(root, 20)
ld_time = time.perf_counter() - t0
print(f"   top20 dirs: {ld_time:.3f}s")

total = scan_time + ann_time
print(f"\n   ⚡ Total (scan + annotate): {total:.3f}s")

# ── Benchmark: User profile scan ────────────────────────────────────
user_home = os.path.expanduser("~")
print(f"\n⏱️  Benchmark: scanning {user_home}")

t0 = time.perf_counter()
scanner2 = DiskScanner(user_home, max_workers=16)
root2 = scanner2.scan()
scan2_time = time.perf_counter() - t0

t0 = time.perf_counter()
annotate_tree(root2)
ann2_time = time.perf_counter() - t0

print(f"   Scanned {scanner2.scanned_files:,} files, {scanner2.scanned_folders:,} folders")
print(f"   Total size: {root2.total_size / 1e9:.1f} GB")
print(f"   Scan time:  {scan2_time:.3f}s")
print(f"   Annotate:   {ann2_time:.3f}s")
print(f"   ⚡ Total:    {scan2_time + ann2_time:.3f}s")

print("\n✅ All tests passed!")
