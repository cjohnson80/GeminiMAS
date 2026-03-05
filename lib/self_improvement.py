import os
import json
import logging
from lib.config_manager import load_local_config

class SelfImprover:
    def __init__(self, config_path='local_config.json'):
        self.config_path = config_path

    def disable_feature(self, feature_name):
        """Disables resource-heavy features to comply with Celeron constraints."""
        try:
            with open(self.config_path, 'r+') as f:
                config = json.load(f)
                if 'disabled_features' not in config:
                    config['disabled_features'] = []
                if feature_name not in config['disabled_features']:
                    config['disabled_features'].append(feature_name)
                f.seek(0)
                json.dump(config, f, indent=4)
                f.truncate()
            load_local_config()
            logging.info(f'Feature {feature_name} disabled successfully.')
        except Exception as e:
            logging.error(f'Failed to disable feature: {e}')

    def optimize_threads(self, thread_count):
        """Ensures thread usage respects max_threads limit."""
        MAX_THREADS = 2
        return min(thread_count, MAX_THREADS)