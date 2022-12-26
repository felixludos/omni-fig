from typing import Union, Any, Type, Optional
from pathlib import Path
from omnibelt import Exporter, ExportManager, get_now
from omnibelt import exporting_common as _

from .config import ConfigNode
from .top import create_config


class ConfigExporter(Exporter, extensions=['.fig.yml', '.fig.yaml'], types=[ConfigNode]):
	@staticmethod
	def _load_export(path: Union[Path, str], src: Type[ExportManager], **kwargs) -> Any:
		return create_config(path, **kwargs)

	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str],
	                    src: Type[ExportManager], **kwargs) -> Optional[Path]:

		if path.suffix.endswith('.toml') or path.suffix.endswith('.tml'):
			return src.export(payload.to_python(), path=path, fmt='toml')
		elif path.suffix.endswith('.json'):
			return src.export(payload.to_python(), path=path, fmt='json')
		else:
			lines = [
				f'# Exported on {get_now()}',
			    payload.to_yaml()
			]
			return src.export('\n'.join(lines), path=path, fmt=str)

















