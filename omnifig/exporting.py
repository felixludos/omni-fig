from typing import Union, Any, Type, Optional
from pathlib import Path
import yaml
from omnibelt import Exporter, ExportManager, get_now
from omnibelt import exporting_common as _

from .abstract import AbstractConfig
# from .config.nodes import ConfigSparseNode, ConfigDenseNode
from .top import create_config



class ConfigExporter(Exporter, extensions=['.fig.yml', '.fig.yaml'], types=[AbstractConfig]):
	'''
	Exporter for config objects, can load and save config objects in four formats: json, yaml, toml,
	and the native ".fig.yml" format (which is equivalent to yaml).
	'''

	@staticmethod
	def _load_export(path: Union[Path, str], src: Type[ExportManager], **kwargs) -> Any:
		'''
		Load a config object from a file. Will use the config manager of the current project,
		see ``ConfigManager.create_config``.

		Args:
			path: the path to the file to load
			src: manager used for delegation (not used)
			**kwargs: additional arguments to pass to the load

		Returns:
			the loaded config object

		'''
		return create_config(path, **kwargs)


	@staticmethod
	def _export_payload(payload: Any, path: Union[Path, str], src: Type[ExportManager]) -> Optional[Path]:
		'''
		Exports the given payload to the given path.

		Args:
			payload: config object to be exported
			path: destination path for the export
			src: manager used for delegating the export to a different format

		Returns:
			the path to the exported file (or None if the export failed)

		'''

		if path.suffix.endswith('.toml') or path.suffix.endswith('.tml'):
			return src.export(payload.to_python(), path=path, fmt='toml')
		elif path.suffix.endswith('.json'):
			return src.export(payload.to_python(), path=path, fmt='json')
		else:
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
			return src.export('\n'.join(lines), path=path, fmt=str)



# def _sparse_config_node_representer(dumper, node):
# 	return dumper.represent_dict({k: v for k, v in node.peek_named_children(silent=True)})
# yaml.add_representer(ConfigSparseNode, _sparse_config_node_representer)
#
# def _dense_config_node_representer(dumper, node):
# 	return dumper.represent_list([v for k, v in node.peek_named_children(silent=True)])
# yaml.add_representer(ConfigDenseNode, _dense_config_node_representer)










