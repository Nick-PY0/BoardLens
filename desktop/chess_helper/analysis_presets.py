"""Named settings for live analysis, independent of other board features."""
from pathlib import Path
from . import engine_config,engine_library
from .presets import PresetStore,FIELDS


class AnalysisPresets:
    def __init__(self,window):
        self.window=window
        self.store=PresetStore()

    def preset_values(self):
        w=self.window;values,_=w.phone.schema();result={key:values[key] for key in FIELDS if key in values}
        result['engine_identity']=engine_config.entry(w).identity
        if result['engine_identity']=='custom':result['custom_engine']=w.custom_engine.text()
        return result

    def save_preset(self,name,identity=None):
        identity=self.store.save(name,self.preset_values(),identity);self.refresh_presets();return identity

    def refresh_presets(self):
        w=self.window;w.preset_combo.blockSignals(True);w.preset_combo.clear();w.preset_combo.addItem('Manual',None)
        for item in self.store.list():w.preset_combo.addItem(item['name'],item['id'])
        w.preset_combo.blockSignals(False)

    def apply_preset(self,identity):
        item=self.store.get(identity);values=dict(item['settings']);entry=engine_library.BY_ID.get(values.pop('engine_identity','stockfish'))
        if entry is None:raise ValueError('This preset uses an unknown engine.')
        if entry.kind=='custom':
            if not Path(values.get('custom_engine',self.window.custom_engine.text())).is_file():raise ValueError('Choose the custom engine executable before loading this preset.')
        elif entry.kind in ('stockfish','flounder'):
            engine_config.command(self.window,0)
        elif not engine_library.available(entry):raise ValueError(f'{entry.label} is not installed. Download it in Engine library first.')
        values['engine_kind']=engine_library.ENTRIES.index(entry);w=self.window;w._applying_preset=True
        try:w.phone.apply_settings(values)
        finally:w._applying_preset=False
        w.engine_configuration_changed();w.visual_settings_changed();w.queue_autosave()
        index=w.preset_combo.findData(identity);w.preset_combo.blockSignals(True);w.preset_combo.setCurrentIndex(index);w.preset_combo.blockSignals(False)

    def snapshot(self):
        return [{'id':p['id'],'name':p['name'],'builtin':p['builtin']} for p in self.store.list()]

    def command(self,name,payload):
        if name=='apply_preset':self.apply_preset(str(payload.get('id','')))
        elif name=='save_preset':self.save_preset(payload.get('name',''),payload.get('id'));return 'Preset saved.'
        elif name=='delete_preset':self.store.delete(str(payload.get('id','')));self.refresh_presets()
        else:raise ValueError('Unknown preset command.')
        return 'Applied'
