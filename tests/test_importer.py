from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from itchy.game import Arithmetic, Comparison
from itchy.importer import PythonImporter


def test_imported_literals_use_python_values_and_variable_references(tmp_path):
    project = {'targets': [{'isStage': True, 'name': 'Stage',
                           'variables': {'speed': ['G.Spd', 1]}, 'lists': {},
                           'blocks': {}, 'broadcasts': {}}]}
    with ZipFile(BytesIO(), 'w') as archive:
        importer = PythonImporter(Path('test.sb3'), project, archive, tmp_path)
        assert importer._literal('Stage', [12, 'G.Spd', 'speed']) == 'vars.G_Spd'
        assert importer._literal('Stage', [10, '1']) == "'1'"
        assert importer._literal('Stage', [4, '4']) == '4'
        assert importer._literal('Stage', [4, '']) == "ScratchLiteral(4, '')"
        for opcode, inputs, expected in (
            ('operator_add', {'NUM1': '2', 'NUM2': '3'}, Arithmetic),
            ('operator_equals', {'OPERAND1': "'1'", 'OPERAND2': "'1'"}, Comparison),
            ('operator_lt', {'OPERAND1': '2', 'OPERAND2': '3'}, Comparison),
        ):
            source = importer._semantic_block(opcode, inputs, {}, {}, 'Stage', as_command=False)
            assert isinstance(eval(source, {'Arithmetic': Arithmetic, 'Comparison': Comparison}), expected)


def test_imported_arithmetic_uses_operators_with_text_variables(tmp_path):
    from types import SimpleNamespace
    from itchy.game import StringVariable
    project = {'targets': [{'isStage': True, 'name': 'Stage', 'blocks': {}}]}
    with ZipFile(BytesIO(), 'w') as archive:
        importer = PythonImporter(Path('test.sb3'), project, archive, tmp_path)
        source = importer._semantic_block(
            'operator_divide', {'NUM1': '100', 'NUM2': 'vars.zoom'}, {}, {},
            'Stage', as_command=False,
        )
        assert source == '(100 / vars.zoom)'
        variables = SimpleNamespace(zoom=StringVariable('zoom', '10'))
        expression = eval(source, {'vars': variables})
        assert isinstance(expression, Arithmetic)
        assert expression.left == 100
        assert expression.right is variables.zoom
        source = importer._semantic_block(
            'operator_lt', {'OPERAND1': 'vars.zoom', 'OPERAND2': "'100'"}, {}, {},
            'Stage', as_command=False,
        )
        assert source == '(vars.zoom < 100)'
        assert isinstance(eval(source, {'vars': variables}), Comparison)


def test_importer_flattens_only_single_else_if_stack(tmp_path):
    project = {'targets': [{'isStage': True, 'name': 'Stage', 'blocks': {}}]}
    with ZipFile(BytesIO(), 'w') as archive:
        importer = PythonImporter(Path('test.sb3'), project, archive, tmp_path)
        single = "(if_(b).then((move_x(2),)).else_((move_x(3),)),)"
        source = importer._semantic_block('control_if_else', {'CONDITION': 'a'}, {},
                                         {'SUBSTACK': '(move_x(1),)', 'SUBSTACK2': single},
                                         'Stage', as_command=False)
        assert '.elif_(b)' in source
        assert '.else_((move_x(3),))' in source
        multiple = '(if_(b).then((move_x(2),)), move_x(4))'
        source = importer._semantic_block('control_if_else', {'CONDITION': 'a'}, {},
                                         {'SUBSTACK': '(move_x(1),)', 'SUBSTACK2': multiple},
                                         'Stage', as_command=False)
        assert '.elif_' not in source


def test_import_splits_sprite_modules_and_scopes_variables(tmp_path):
    import json
    import subprocess
    import sys
    from itchy.importer import import_project
    project = {'targets': [
        {'isStage': True, 'name': 'Stage', 'variables': {'global': ['score', 0]},
         'blocks': {}, 'lists': {}, 'broadcasts': {}},
        {'isStage': False, 'name': 'Player', 'variables': {'local': ['health', 10]},
         'lists': {}, 'blocks': {
             'hat': {'opcode': 'event_whenflagclicked', 'topLevel': True, 'next': 'set'},
             'set': {'opcode': 'data_setvariableto', 'next': None,
                     'fields': {'VARIABLE': ['health', 'local']},
                     'inputs': {'VALUE': [3, [12, 'score', 'global'], [10, '']]}}
         }, 'costumes': []},
    ]}
    source = tmp_path / 'test.sb3'
    with ZipFile(source, 'w') as archive:
        archive.writestr('project.json', json.dumps(project))
    directory = tmp_path / 'imported'
    import_project(source, directory)
    sprite = (directory / 'sprite_player.py').read_text()
    assert 'class svars:' in sprite
    assert 'svars.health.set(vars.score)' in sprite
    assert 'health' not in (directory / 'vars.py').read_text()
    assert 'Sprite(' not in (directory / 'game.py').read_text()
    subprocess.run([sys.executable, '-c',
                    'from pathlib import Path; from itchy.project import load_game; '
                    'from itchy.compiler import compile_game; '
                    f'compile_game(load_game(Path({str(directory)!r})))'], check=True)
