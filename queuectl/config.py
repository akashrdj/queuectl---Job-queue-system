# congig management

import json
from pathlib import Path
from typing import Any


class Config:
    
    
    dconfig = {
        'max_retries': 3,
        'backoff_base': 2,
        'db_path': 'queuectl.db',
        'configpath': 'queuectl_config.json'
    }
    
    def __init__(self, configpath: str = 'queuectl_config.json'):
        
        self.configpath = Path(configpath)
        
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        
        if self.configpath.exists():
            try:
                with open(self.configpath, 'r') as f:
                    
                    loaded = json.load(f)
                    

                    config = self.dconfig.copy()

                    config.update(loaded)
                    return config
            except Exception:
                pass
        return self.dconfig.copy()
    
    def _save_config(self) -> None:
        
        with open(self.configpath, 'w') as f:

            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
    
        self.config[key] = value
        self._save_config()
    
    def list_all(self) -> dict:
        
        return self.config.copy()
