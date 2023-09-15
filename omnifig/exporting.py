from typing import Union, Any, Type, Optional
from pathlib import Path
import yaml
from omnibelt import SimpleExporterBase, ExportManager, get_now
from omnibelt.exporting import ExporterBase, AbstractExportManager
from omnibelt import exporting_common as _

# from .abstract import AbstractConfig
# from .config.nodes import ConfigSparseNode, ConfigDenseNode
from .config import ConfigNode
from .top import create_config



class ConfigExporter(SimpleExporterBase, extensions=['.fig.yml', '.fig.yaml'], types=ConfigNode):
	'''
	Exporter for config objects, can load and save config objects in four formats: json, yaml, toml,
	and the native ".fig.yml" format (which is equivalent to yaml).
	'''

	def export_payload(self, src: AbstractExportManager, payload: ConfigNode, path: Path, *,
					   fmt: Optional[str] = None, **kwargs) -> Path:
		'''
		Exports the given payload to the given path.

		Args:
			src: manager used for delegating the export to a different format
			payload: config object to be exported
			path: destination path for the export
			fmt: format to use for the export (if None, will be inferred from the path, defaults to `.fig.yml`)

		Returns:
			the path to the exported file (or None if the export failed)

		'''
		if path.suffix.endswith('.toml') or path.suffix.endswith('.tml'):
			return src.export(payload.to_python(), path=path, fmt='toml')
		elif path.suffix.endswith('.json'):
			return src.export(payload.to_python(), path=path, fmt='json')
		else:
			return super().export_payload(src, payload, path, fmt=fmt, **kwargs)


	@staticmethod
	def _export_payload(payload: Any, path: Path, **kwargs) -> None:
		lines = [
			f'# Exported on {get_now()}',
		]

		cro = getattr(payload, 'cro', None)
		if cro is not None:
			lines.append(f'# Config resolution order (cro): {cro}')

		bases = getattr(payload, 'bases', None)
		if bases is not None:
			lines.append(f'# Config bases: {bases}')

		lines.append(payload.to_yaml())
		with path.open('w') as f:
			f.write('\n'.join(lines))


	@staticmethod
	def _load_payload(path: Path, **kwargs) -> Any:
		'''
		Load a config object from a file. Will use the config manager of the current project,
		see ``ConfigManager.create_config``.

		Args:
			path: the path to the file to load
			**kwargs: additional arguments to pass to the load

		Returns:
			the loaded config object

		'''
		return create_config(path, **kwargs)









