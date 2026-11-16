"""Конфигурация и модель пресетов VibranceHub."""
from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

APP_NAME = 'VibranceHub'
APP_VERSION = '1.0.0'

CATEGORIES = ['Аркада', 'Война', 'Реализм', 'Рабочий стол', 'Своё']

CAT_COLORS = {
    'Аркада': '#ff9f0a',
    'Война': '#30d158',
    'Реализм': '#bf5af2',
    'Рабочий стол': '#0a84ff',
    'Своё': '#ff375f',
}


@dataclass
class Preset:
    id: str
    name: str
    category: str
    vibrance: int = 50
    gamma: float = 1.0
    brightness: int = 0
    contrast: int = 100
    warmth: int = 0
    builtin: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> 'Preset':
        return Preset(
            id=str(d.get('id') or uuid.uuid4().hex[:8]),
            name=str(d.get('name') or 'Пресет'),
            category=d.get('category') if d.get('category') in CATEGORIES else 'Своё',
            vibrance=int(d.get('vibrance', 50)),
            gamma=float(d.get('gamma', 1.0)),
            brightness=int(d.get('brightness', 0)),
            contrast=int(d.get('contrast', 100)),
            warmth=int(d.get('warmth', 0)),
            builtin=bool(d.get('builtin', False)),
        )

    def is_neutral(self) -> bool:
        return (self.gamma == 1.0 and self.brightness == 0
                and self.contrast == 100 and self.warmth == 0)


def builtin_presets() -> list[Preset]:
    """Заготовленные пресеты (три семейства игровых фильтров + рабочий стол)."""
    return [
        Preset('std', 'Стандарт', 'Рабочий стол', 50, builtin=True),
        Preset('vivid', 'Яркий', 'Рабочий стол', 70, builtin=True),
        Preset('arcade', 'Аркада (CS2, Valorant)', 'Аркада', 90, contrast=103, builtin=True),
        Preset('arcade_max', 'Аркадный максимум', 'Аркада', 100, contrast=105, builtin=True),
        Preset('war', 'Война (видно в тенях)', 'Война', 35,
               gamma=1.15, brightness=12, contrast=88, builtin=True),
        Preset('realism', 'Реализм (RDR2, Witcher)', 'Реализм', 65, contrast=104, builtin=True),
        Preset('movie', 'Кино (тёплый)', 'Рабочий стол', 60,
               gamma=1.05, warmth=25, builtin=True),
        Preset('night', 'Ночной', 'Рабочий стол', 30,
               warmth=45, brightness=-6, builtin=True),
    ]


def app_data_dir() -> Path:
    base = os.environ.get('APPDATA')
    if base:
        d = Path(base) / APP_NAME
    else:
        d = Path.home() / ('.' + APP_NAME.lower())
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return app_data_dir() / 'config.json'


def resource_path(rel: str) -> Path:
    """Путь к ресурсу пакета (учитывает PyInstaller --onefile)."""
    if getattr(sys, 'frozen', False):
        base = getattr(sys, '_MEIPASS', None)
        if base:
            return Path(base) / rel
    return Path(__file__).resolve().parents[2] / rel


class Config:
    def __init__(self) -> None:
        self.presets: list[Preset] = builtin_presets()
        self.rules: list[dict] = []      # [{'process': 'cs2.exe', 'preset': 'arcade'}]
        self.desktop_preset: str = 'std'
        self.autoshift_enabled: bool = True
        self.poll_interval_ms: int = 1000
        self.hotkeys_enabled: bool = True
        self.autostart: bool = False
        self.start_minimized: bool = False
        self.notify: bool = True
        self.apply_on_start: bool = True
        self.restore_on_exit: bool = True
        self.load()

    # ---------------- persistence ----------------
    def load(self) -> None:
        p = config_path()
        if not p.exists():
            self.save()
            return
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            return
        if not isinstance(data, dict):
            return
        presets: list[Preset] = []
        for d in data.get('presets', []):
            try:
                presets.append(Preset.from_dict(d))
            except Exception:
                pass
        have = {pr.id for pr in presets}
        for b in builtin_presets():
            if b.id not in have:
                presets.append(b)
        self.presets = presets
        rules: list[dict] = []
        for r in data.get('rules', []):
            if isinstance(r, dict) and r.get('process') and r.get('preset'):
                rules.append({'process': self.norm_process(str(r['process'])),
                              'preset': str(r['preset'])})
        self.rules = rules
        self.desktop_preset = str(data.get('desktop_preset', 'std'))
        self.autoshift_enabled = bool(data.get('autoshift_enabled', True))
        self.poll_interval_ms = int(data.get('poll_interval_ms', 1000))
        self.hotkeys_enabled = bool(data.get('hotkeys_enabled', True))
        self.autostart = bool(data.get('autostart', False))
        self.start_minimized = bool(data.get('start_minimized', False))
        self.notify = bool(data.get('notify', True))
        self.apply_on_start = bool(data.get('apply_on_start', True))
        self.restore_on_exit = bool(data.get('restore_on_exit', True))

    def save(self) -> None:
        data = {
            'version': 1,
            'presets': [pr.to_dict() for pr in self.presets],
            'rules': self.rules,
            'desktop_preset': self.desktop_preset,
            'autoshift_enabled': self.autoshift_enabled,
            'poll_interval_ms': self.poll_interval_ms,
            'hotkeys_enabled': self.hotkeys_enabled,
            'autostart': self.autostart,
            'start_minimized': self.start_minimized,
            'notify': self.notify,
            'apply_on_start': self.apply_on_start,
            'restore_on_exit': self.restore_on_exit,
        }
        try:
            p = config_path()
            tmp = p.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            tmp.replace(p)
        except Exception:
            pass

    def reset_to_defaults(self) -> None:
        self.presets = builtin_presets()
        self.rules = []
        self.desktop_preset = 'std'
        self.autoshift_enabled = True
        self.poll_interval_ms = 1000
        self.hotkeys_enabled = True
        self.start_minimized = False
        self.notify = True
        self.apply_on_start = True
        self.restore_on_exit = True
        self.save()

    # ---------------- helpers ----------------
    @staticmethod
    def norm_process(name: str) -> str:
        n = name.strip().lower().replace('/', '\\')
        n = n.rsplit('\\', 1)[-1]
        if n and '.' not in n:
            n += '.exe'
        return n

    def preset_by_id(self, pid: str | None) -> Preset | None:
        for pr in self.presets:
            if pr.id == pid:
                return pr
        return None

    def add_preset(self, pr: Preset) -> None:
        self.presets.append(pr)
        self.save()

    def remove_preset(self, pid: str) -> None:
        self.presets = [pr for pr in self.presets if pr.id != pid]
        self.rules = [r for r in self.rules if r['preset'] != pid]
        if self.desktop_preset == pid:
            self.desktop_preset = 'std'
        self.save()

    def find_rule(self, process: str) -> dict | None:
        for r in self.rules:
            if r['process'] == process:
                return r
        return None

    def add_rule(self, process: str, preset_id: str) -> bool:
        proc = self.norm_process(process)
        if not proc or not self.preset_by_id(preset_id):
            return False
        if self.find_rule(proc):
            return False
        self.rules.append({'process': proc, 'preset': preset_id})
        self.save()
        return True

    def remove_rule(self, process: str) -> None:
        self.rules = [r for r in self.rules if r['process'] != process]
        self.save()
