"""Validate real ComfyUI V3 schemas and example wiring without cloud calls.

Run: python scripts/verify_comfy_contracts.py --comfy-root /path/to/ComfyUI
Use a ComfyUI Python environment with its dependencies installed.
"""
import argparse
import asyncio
import inspect
import json
import tempfile
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--comfy-root", required=True)
args = parser.parse_args()
root = Path(args.comfy_root).resolve()
if not (root / "comfy_api/latest/_io.py").is_file():
    parser.error("--comfy-root must contain actual ComfyUI API source")
project = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(project))
sys.argv = [sys.argv[0], "--cpu"]
from comfy_api.latest import _io as internal_io, io
from mediakit_toolkit.extension import comfy_entrypoint
from mediakit_toolkit.nodes.video_editing import _ordered_media

nodes = asyncio.run(asyncio.run(comfy_entrypoint()).get_node_list())
by_id = {}
for node in nodes:
    schema = node.define_schema()
    schema.validate()
    by_id[schema.node_id] = node
    parameters = inspect.signature(node.execute).parameters
    assert all(item.id in parameters for item in schema.inputs), schema.node_id
    assert len({item.id for item in schema.outputs}) == len(schema.outputs), schema.node_id

multi_ids = {"MediaKitConcatVideo": ("videos", "video", 100), "MediaKitStitchVideo": ("videos", "video", 3),
             "MediaKitConcatAudio": ("audios", "audio", 100), "MediaKitMixAudio": ("audios", "audio", 100)}
for node_id, (group, kind, maximum) in multi_ids.items():
    inputs = internal_io.create_input_dict_v1(by_id[node_id].define_schema().inputs)
    live = {f"{group}.{kind}_2": "second", f"{group}.{kind}_1": "first"}
    flat, _hidden, data = internal_io.get_finalized_class_inputs(inputs, live)
    nested = internal_io.build_nested_inputs(live, data)
    assert _ordered_media(nested[group], kind, maximum) == ["first", "second"], node_id

workflows = ["mediakit_video_edit_basic.json", "mediakit_video_concat.json", "mediakit_video_audio_edit.json"]
for name in workflows:
    graph = json.loads((project / "example_workflows" / name).read_text())
    graph_nodes = {node["id"]: node for node in graph["nodes"]}
    for node in graph_nodes.values():
        assert len({x["name"] for x in node["inputs"]}) == len(node["inputs"]), (name, node["type"])
        if node["type"] not in by_id:
            continue
        schema = by_id[node["type"]].define_schema()
        input_dict = internal_io.create_input_dict_v1(schema.inputs)
        flat, _, _ = internal_io.get_finalized_class_inputs(input_dict, {x["name"]: True for x in node["inputs"]})
        valid_inputs = flat["required"] | flat["optional"]
        for item in node["inputs"]:
            assert item["name"] in valid_inputs, (name, item["name"])
            assert item["type"] == valid_inputs[item["name"]][0], (name, item["name"])
        widgets = [x for x in schema.inputs if isinstance(x, internal_io.WidgetInput)]
        assert len(node["widgets_values"]) == len(widgets), (name, node["type"])
        for value, item in zip(node["widgets_values"], widgets):
            if isinstance(item, io.Combo.Input):
                assert value in item.options, (name, item.id, value)
        assert [x["type"] for x in node["outputs"]] == [x.get_io_type() for x in schema.outputs]
    for link_id, source, source_slot, dest, dest_slot, type_name in graph["links"]:
        output = graph_nodes[source]["outputs"][source_slot]
        input = graph_nodes[dest]["inputs"][dest_slot]
        assert link_id in output["links"] and input["link"] == link_id
        assert output["type"] == input["type"] == type_name
from mediakit_toolkit.media_bridge import download_video_output, materialize_video
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "native.mp4"
    """Fixture: actual VideoFromFile construction/stream access only, not decoding."""
    path.write_bytes(b"verification-only")
    video = asyncio.run(download_video_output(str(path)))
    with materialize_video(video) as native_path:
        assert native_path == path.resolve()
print(json.dumps({"passed": True, "real_schemas": len(nodes), "autogrow_nodes": len(multi_ids),
                  "p1_workflows_checked": len(workflows), "cloud_tasks": 0,
                  "limitations": ["No browser/frontend import", "No MediaKit cloud end-to-end execution"]}))
