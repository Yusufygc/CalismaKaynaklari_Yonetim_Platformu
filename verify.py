"""Ajan görevlerinin kapanış doğrulaması. Kullanım: python verify.py [görev kimliği ...]"""
import json
import sys
from pathlib import Path

TOOL_ROOT = "C:\\Users\\yusuf\\AppData\\Local\\Programs\\GitClean Archiver\\_internal"
PROJECT = "C:\\2UYGULAMALAR\\P011-Kaynak_Yonetim_Platformu"

sys.path.insert(0, TOOL_ROOT)
from src.services.project_service import ProjectService  # noqa: E402

service = ProjectService()
service.set_project(Path(PROJECT))
result = service.verify_agent_tasks(Path(__file__).resolve().parent, only=sys.argv[1:] or None)
print(json.dumps(result, ensure_ascii=False, indent=1))
