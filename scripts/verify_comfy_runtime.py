"""Real localhost ComfyUI frontend/queue smoke checks; never run valid cloud editing.

Requires Playwright and an installed Chrome/Chromium. Start an isolated ComfyUI
instance with this plugin and a non-private video fixture in its input folder.
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8197')
parser.add_argument('--browser-executable', required=True)
parser.add_argument('--fixture-file', required=True)
parser.add_argument('--artifacts-dir', required=True)
args = parser.parse_args()
base = args.url.rstrip('/')
parsed = urlparse(base)
if parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
    parser.error('Only an isolated localhost ComfyUI instance is supported')
project = Path(__file__).resolve().parent.parent
output = Path(args.artifacts_dir)
output.mkdir(parents=True, exist_ok=True)

def get(path):
    with urllib.request.urlopen(base + path, timeout=60) as response:
        return json.load(response)


def run_local(prompt, expected_error=None):
    allowed = {'MediaKitEnvironmentCheck', 'LoadVideo', 'SaveVideo', 'PreviewAny',
               'MediaKitExtractAnimatedImage', 'MediaKitAddSubtitle'}
    for node in prompt.values():
        if node['class_type'] not in allowed:
            raise ValueError('Unsafe cloud task in verification prompt')
        if node['class_type'] == 'MediaKitEnvironmentCheck' and node['inputs'].get('run_doctor') is not False:
            raise ValueError('Diagnostics must not call cloud doctor')
        if node['class_type'] == 'MediaKitExtractAnimatedImage' and node['inputs'].get('end_time') != 0:
            raise ValueError('Only pre-submit invalid animation ranges are permitted')
        if node['class_type'] == 'MediaKitAddSubtitle' and node['inputs'].get('subtitles_json') != '{invalid':
            raise ValueError('Only invalid JSON pre-submit subtitle check is permitted')
    request = urllib.request.Request(base + '/prompt', data=json.dumps({'prompt':prompt}).encode(),
                                     headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        submitted = json.load(response)
    prompt_id = submitted['prompt_id']
    for _ in range(120):
        result = get('/history/' + prompt_id).get(prompt_id)
        if result:
            break
        time.sleep(.5)
    else:
        raise RuntimeError('Local queue timed out')
    status = result['status']['status_str']
    errors = [value for name,value in result['status'].get('messages',[]) if name == 'execution_error']
    if expected_error:
        assert status == 'error' and errors, result
        error = errors[-1]
        assert expected_error in error.get('exception_message',''), error
        return {'passed':True,'expected_error':expected_error,'actual_error_type':error.get('exception_type')}
    assert status == 'success' and result['status'].get('completed'), result
    return {'passed':True,'status':status,'outputs':result.get('outputs')}

info = get('/object_info')
stats = get('/system_stats')
assert len([name for name in info if name.startswith('MediaKit')]) == 32
assert args.fixture_file in info['LoadVideo']['input']['required']['file'][1]['options']

from playwright.sync_api import sync_playwright
browser_results = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=args.browser_executable, headless=True)
    page = browser.new_page(viewport={'width':1700,'height':1100})
    page_errors = []
    page.on('pageerror', lambda error: page_errors.append(str(error)))
    page.goto(base, wait_until='networkidle', timeout=90000)
    page.wait_for_function('window.app?.graph && typeof app.handleFile === "function"', timeout=60000)
    page.keyboard.press('Escape')
    for name in ['mediakit_video_edit_basic.json','mediakit_video_concat.json','mediakit_video_audio_edit.json']:
        raw = (project/'example_workflows'/name).read_text()
        expected = json.loads(raw)
        await_import = '''async ({name,text}) => { await app.handleFile(new File([text],name,{type:"application/json"})); }'''
        page.evaluate(await_import, {'name':name,'text':raw})
        page.wait_for_timeout(1000)
        state = page.evaluate('''async () => ({
            nodes:app.graph._nodes.map(n=>({id:String(n.id),type:n.type,error:!!n.has_errors,
              inputs:n.inputs?.map(i=>({name:i.name,type:i.type,link:i.link})),
              widgets:n.widgets?.map(w=>({name:w.name,value:w.value}))})),
            prompt:await app.graphToPrompt()})''')
        assert len(state['nodes']) == len(expected['nodes']), name
        assert not any(node['error'] for node in state['nodes']), name
        actual = state['prompt']['output']
        expected_nodes = {str(node['id']):node for node in expected['nodes']}
        for node in state['nodes']:
            assert node['type'] == expected_nodes[node['id']]['type'], name
        for link in expected['links']:
            _,source,source_slot,target,target_slot,_ = link
            expected_input = expected_nodes[str(target)]['inputs'][target_slot]['name']
            assert actual[str(target)]['inputs'][expected_input] == [str(source),source_slot], (name,expected_input)
        if name == 'mediakit_video_concat.json':
            connected = [item for item in state['nodes'][2]['inputs'] if item.get('link') is not None]
            assert [item['name'] for item in connected] == ['videos.video_1','videos.video_2']
            assert actual['3']['inputs']['transitions'] == ''
        save = actual['4']['inputs']
        assert isinstance(save['filename_prefix'],str) and save['filename_prefix']
        if actual['4']['class_type'] == 'SaveVideo':
            assert save['format'] == 'auto' and save['format.codec'] == 'auto'
        (output/(name+'.browser-state.json')).write_text(json.dumps(state,ensure_ascii=False,indent=2))
        page.screenshot(path=str(output/(name+'.png')))
        browser_results.append({'workflow':name,'passed':True,'nodes':len(state['nodes'])})
    assert not page_errors, page_errors
    browser.close()

fixture={'class_type':'LoadVideo','inputs':{'file':args.fixture_file}}
queue = {}
queue['diagnostic'] = run_local({
    '1':{'class_type':'MediaKitEnvironmentCheck','inputs':{'run_doctor':False}},
    '2':{'class_type':'PreviewAny','inputs':{'source':['1',0]}}})
queue['local_video_save'] = run_local({'1':fixture,
    '2':{'class_type':'SaveVideo','inputs':{'video':['1',0],'filename_prefix':'p1_verification/local',
                                         'format':'mp4','format.codec':'h264'}}})
queue['invalid_animation'] = run_local({'1':fixture,
    '2':{'class_type':'MediaKitExtractAnimatedImage','inputs':{'video':['1',0],'start_time':0.,'end_time':0.,
          'output_format':'gif','run_mode':'auto','poll_interval_seconds':10,'max_poll_attempts':720}},
    '3':{'class_type':'PreviewAny','inputs':{'source':['2',2]}}},'动图结束时间必须大于起始时间')
queue['invalid_subtitle'] = run_local({'1':fixture,
    '2':{'class_type':'MediaKitAddSubtitle','inputs':{'video':['1',0],'subtitle_url':'','subtitles_json':'{invalid',
          'subtitle_font_type':'sy_black','subtitle_pos_preset':'bottom_center','subtitle_font_size':50,
          'subtitle_font_color':'#FFFFFFFF','subtitle_text_effect':'','run_mode':'auto',
          'poll_interval_seconds':10,'max_poll_attempts':720}},
    '3':{'class_type':'PreviewAny','inputs':{'source':['2',0]}}},'字幕内容列表不是合法 JSON')

report = {'passed':True,'comfyui':stats['system']['comfyui_version'],
          'frontend':stats['system']['required_frontend_version'],'loaded_plugin_nodes':32,
          'frontend_imports':browser_results,'local_queue_checks':queue,'cloud_tasks':0,
          'limitations':['No successful MediaKit cloud editing execution','Only specified three example imports checked']}
(output/'runtime-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
