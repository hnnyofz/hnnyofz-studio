"""Extend the existing head viewer with independent true front/back hair parts."""
from pathlib import Path
import argparse,json,hashlib,subprocess
import build_head_viewers as base
def build(project,out,blender="blender",node="node"):
 project=Path(project).resolve();out=Path(out).resolve();base.build(project,out,blender,node)
 cfg=json.loads((project/'realtime.json').read_text());runtime=(out/'runtime.js').read_text();old=runtime
 def change(a,b):
  nonlocal runtime
  assert runtime.count(a)==1,(a,runtime.count(a));runtime=runtime.replace(a,b)
 ids=lambda labels:[list(cfg['parts']).index(s)+1 for s in labels]
 front=ids(cfg['frontHairPartNames']);back=ids(cfg['backHairPartNames'])
 needle="if((mode==='hair'&&!isHair)||(mode==='face'&&isHair))continue;"
 change(needle,f"if((mode==='hair'&&!isHair)||(mode==='face'&&isHair)||({json.dumps(front)}.includes(c.structure)&&!$('frontHair').checked)||({json.dumps(back)}.includes(c.structure)&&!$('backHair').checked))continue;")
 helper="""function hairSectionTag(){return $('frontHair').checked?($('backHair').checked?'both':'front'):($('backHair').checked?'back':'none')}
function hairSectionLabel(){return {both:'前发 + 后发',front:'仅前发',back:'仅后发',none:'无头发'}[hairSectionTag()]}
"""
 change('function geometry(){',helper+'function geometry(){')
 change("for(const id of ['outline','structural','palette','displayMode'])$(id).onchange=()=>{dirty=true;$('sequenceDownload').hidden=true;$('saved').hidden=true};", "for(const id of ['outline','structural','palette','displayMode','frontHair','backHair'])$(id).onchange=()=>{const face=$('displayMode').value==='face';$('frontHair').disabled=face;$('backHair').disabled=face;dirty=true;$('sequenceDownload').hidden=true;$('saved').hidden=true};")
 change("+$('displayMode').value+'.png'", "+$('displayMode').value+'-'+hairSectionTag()+'.png'")
 change("+' 透明 PNG'", "+' · '+hairSectionLabel()+' 透明 PNG'")
 change("+$('displayMode').value+'.zip'", "+$('displayMode').value+'-'+hairSectionTag()+'.zip'")
 change("hiddenHead:$('displayMode').value==='hair',sourceSHA256", "hiddenHead:$('displayMode').value==='hair',frontHair:$('frontHair').checked,backHair:$('backHair').checked,hairSections:hairSectionTag(),splitPlane:{axis:'Y',value:0},sourceSHA256")
 change("im.dataset.pitch=state.pitch;", "im.dataset.pitch=state.pitch;im.dataset.frontHair=$('frontHair').checked;im.dataset.backHair=$('backHair').checked;")
 page=(out/'preview.html').read_text();assert old in page;page=page.replace(old,runtime)
 start=page.index('<label class="display-mode">');end=page.index('</label>',start)+len('</label>')
 controls='<div class="hair-sections" role="group" aria-label="前后发显示"><span>头发分区</span><label><input id="frontHair" type="checkbox" checked>前发</label><label><input id="backHair" type="checkbox" checked>后发（含马尾）</label></div>'
 if not 'hairband' in cfg['parts']:controls=controls.replace('后发（含马尾）','后发')
 page=page[:end]+controls+page[end:]
 page=page.replace('</style>','.hair-sections{grid-column:1/-1;display:flex;flex-wrap:wrap;align-items:center;gap:12px 24px;padding:4px 0}.hair-sections label{display:flex;align-items:center;gap:6px}.hair-sections input{width:16px;height:16px;accent-color:var(--blue,#35649b)}</style>')
 (out/'runtime.js').write_text(runtime);(out/'preview.html').write_text(page)
 report=json.loads((out/'build.json').read_text());report.update(runtimeSHA256=hashlib.sha256(runtime.encode()).hexdigest(),frontHairPartIDs=front,backHairPartIDs=back,independentSectionExport=True)
 (out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));subprocess.run([str(node),'--check',str(out/'runtime.js')],check=True)
 print('SECTION_VIEWER',out)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--out',required=True);p.add_argument('--blender',default='blender');p.add_argument('--node',default='node');a=p.parse_args();build(a.project,a.out,a.blender,a.node)
