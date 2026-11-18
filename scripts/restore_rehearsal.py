"""Restore the latest local backup into a new disposable schema on the isolated DB."""
from pathlib import Path
import gzip,json,subprocess,tarfile,time
import pymysql
ROOT=Path(__file__).resolve().parents[3]
SITE=ROOT/"sites/grc.local"
conf=json.loads((SITE/"site_config.json").read_text())
sock=str(ROOT/"sites/.grc-db/mysql.sock")
assert conf["db_socket"]==sock and conf["db_name"]=="grc_local"
backup=max((SITE/"private/backups").glob("*-database.sql.gz"),key=lambda p:p.stat().st_mtime)
schema="grc_restore_"+str(int(time.time()))
connection=pymysql.connect(user="frappe",unix_socket=sock,autocommit=True)
with connection.cursor() as cursor:
 cursor.execute("CREATE DATABASE `"+schema+"` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
try:
 with gzip.open(backup,"rb") as source:
  result=subprocess.run(["mariadb","--socket="+sock,"--user=frappe",schema],input=source.read(),capture_output=True)
 assert result.returncode==0,result.stderr.decode()[:500]
 with connection.cursor() as cursor:
  for table in ("IA Maturity Entity","IA Maturity Template","GRC Assessment Assignment","User"):
   cursor.execute("SELECT COUNT(*) FROM `grc_local`.`tab"+table+"`");live=cursor.fetchone()[0]
   cursor.execute("SELECT COUNT(*) FROM `"+schema+"`.`tab"+table+"`");restored=cursor.fetchone()[0]
   assert live==restored,(table,live,restored)
 for archive in (SITE/"private/backups").glob(backup.name.split("-database")[0]+"*files.tar"):
  with tarfile.open(archive) as tar:
   for item in tar:
    assert not item.name.startswith("/") and ".." not in Path(item.name).parts
 print("PASS: database restored into isolated temporary schema; core GRC row counts match; file archives validated.")
finally:
 with connection.cursor() as cursor:
  assert schema.startswith("grc_restore_") and schema.removeprefix("grc_restore_").isdigit()
  cursor.execute("DROP DATABASE `"+schema+"`")
 connection.close()
