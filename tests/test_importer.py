from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from itchy.game import Arithmetic, Comparison
from itchy.importer import PythonImporter


def test_imported_procedures_infer_signature_metadata(tmp_path):
    import json
    import itchy.game as game
    from itchy.compiler import compile_game

    cases = [
        ('Pierc %s %s', ['Dmg', 'x1'], ['', ''], True),
        ('choose %b %s', ['enabled', 'value'], [False, ''], False),
        ('defaults %s %b', ['value', 'enabled'], ['10', 'false'], False),
        ('Goto X: %s Y: %s', ['x', 'y'], ['', ''], False),
        ('Tick', [], [], True),
        ('extra %s', ['value'], ['', '', ''], False),
        ('duplicate %s', ['value'], [''], False),
        ('duplicate %b', ['value'], [False], False),
        ('labels %s %s %s %s %s %s %s',
         ['Data', 'Radius', 'MaxHit', 'Length', 'ListID', 'Type', 'Δ'], [''] * 7, False),
        ('invalid %s %s %s %s', ['not valid', 'class', 'x-y', 'x_y'], [''] * 4, False),
        ('Unzip %s', ['data'], [''], True),
    ]
    blocks = {}
    for index, (code, names, defaults, warp) in enumerate(cases):
        ids = [f'original:{index}:{arg}' for arg in range(len(names))]
        blocks[f'def{index}'] = {
            'opcode': 'procedures_definition', 'next': None,
            'inputs': {'custom_block': [1, f'proto{index}']},
        }
        blocks[f'proto{index}'] = {
            'opcode': 'procedures_prototype',
            'mutation': {'proccode': code, 'argumentids': json.dumps(ids),
                         'argumentnames': json.dumps(names),
                         'argumentdefaults': json.dumps(defaults),
                         'warp': str(warp).lower()},
        }
    project = {'targets': [{'isStage': True, 'name': 'Stage', 'blocks': blocks,
                           'lists': {'data-id': ['data', []]}}]}
    with ZipFile(BytesIO(), 'w') as archive:
        importer = PythonImporter(Path('test.sb3'), project, archive, tmp_path)
    source = '\n'.join(importer.target_lines['Stage'])
    assert "@procedure(warp=True)" in source
    assert 'def Pierc(Dmg, x1):' in source
    assert 'def Unzip(data):' in source
    assert "name='Unzip'" not in source
    assert "argument_names=('data',)" not in source
    assert 'def labels(Data, Radius, MaxHit, Length, ListID, Type, Δ):' in source
    assert "argument_names=('not valid', 'class', 'x-y', 'x_y')" in source
    assert 'def invalid(not_valid, class_, x_y, x_y_2):' in source
    assert 'def choose(enabled: bool, value):' in source
    assert "def defaults(value='10', enabled: bool='false'):" in source
    assert "proccode='Goto X: %s Y: %s'" in source
    assert "@procedure(warp=True)" in source
    assert "argument_defaults=('', '', '')" in source
    assert "proccode='duplicate %s'" in source
    assert "proccode='duplicate %b'" in source
    assert 'argument_ids=' not in source
    namespace = dict(vars(game))
    exec(source, namespace)
    procedures = tuple(namespace[proc['symbol']] for proc in importer.procedures['Stage'].values())
    calls = tuple(proc(*(game.predicate('operator_equals', inputs={'OPERAND1': 0, 'OPERAND2': 1})
                        if arg.boolean else 'test' for arg in proc.arguments))
                  for proc in procedures)
    compiled = compile_game(game.Game('Imported', (), (), stage=game.Sprite(
        'Stage', game.Costume('<svg xmlns="http://www.w3.org/2000/svg"/>', name='empty'),
        (game.on_start(*calls),), procedures=procedures,
    )))
    with ZipFile(BytesIO(compiled)) as archive:
        output = json.loads(archive.read('project.json'))
    output_blocks = output['targets'][0]['blocks'].values()
    prototypes = {block['mutation']['proccode']: block for block in output_blocks
                  if block['opcode'] == 'procedures_prototype'}
    for code, names, defaults, warp in cases:
        mutation = prototypes[code]['mutation']
        assert json.loads(mutation['argumentnames']) == names
        assert json.loads(mutation['argumentdefaults']) == defaults
        assert mutation['warp'] == str(warp).lower()
        for call in output_blocks:
            if call['opcode'] == 'procedures_call' and call['mutation']['proccode'] == code:
                assert call['mutation']['argumentids'] == mutation['argumentids']
                assert set(call['inputs']) == set(json.loads(mutation['argumentids']))


def test_procedure_names_strip_placeholders_and_preserve_labels(tmp_path):
    codes = ['Goto X: %s Y: %s Dir: %s From X: %s Y: %s',
             'Goto X: %b Y: %s Dir: %s From X: %s Y: %s', '%s %b']
    blocks = {
        f'call{i}': {'opcode': 'procedures_call',
                    'mutation': {'proccode': code, 'argumentids': '[]'}}
        for i, code in enumerate(codes)
    }
    project = {'targets': [{'isStage': True, 'name': 'Stage', 'blocks': blocks}]}
    with ZipFile(BytesIO(), 'w') as archive:
        importer = PythonImporter(Path('test.sb3'), project, archive, tmp_path)
        procedures = importer.procedures['Stage']
        assert procedures[codes[0]]['symbol'] == 'Goto_X_Y_Dir_From_X_Y'
        assert procedures[codes[1]]['symbol'] == 'Goto_X_Y_Dir_From_X_Y_2'
        assert procedures[codes[2]]['symbol'] == 'procedure_3'
        assert [proc['proccode'] for proc in procedures.values()] == codes


def test_importer_uses_named_math_helpers(tmp_path):
    from dataclasses import asdict
    import itchy.game as game

    project = {'targets': [{'isStage': True, 'name': 'Stage', 'blocks': {}}]}
    operations = {
        'abs': 'abs_number', 'floor': 'floor', 'ceiling': 'ceil',
        'sqrt': 'sqrt', 'sin': 'sin', 'cos': 'cos', 'tan': 'tan',
        'asin': 'asin', 'acos': 'acos', 'atan': 'atan',
        'ln': 'ln', 'log': 'log10', 'e ^': 'exp', '10 ^': 'pow10',
    }
    with ZipFile(BytesIO(), 'w') as archive:
        importer = PythonImporter(Path('test.sb3'), project, archive, tmp_path)
        for operation, helper in operations.items():
            source = importer._semantic_block(
                'operator_mathop', {'NUM': '12'}, {'OPERATOR': repr(operation)},
                {}, 'Stage', as_command=False,
            )
            assert source == f'{helper}(12)'
            assert asdict(eval(source, vars(game))) == asdict(game.math_op(operation, 12))
        assert importer._semantic_block(
            'operator_mathop', {'NUM': '12'}, {'OPERATOR': "'unknown'"},
            {}, 'Stage', as_command=False,
        ) == "math_op('unknown', 12)"


def test_importer_flattens_left_join_chain(tmp_path):
    project = {'targets': [{'isStage': True, 'name': 'Stage', 'blocks': {}}]}
    with ZipFile(BytesIO(), 'w') as archive:
        importer = PythonImporter(Path('test.sb3'), project, archive, tmp_path)
        source = importer._semantic_block(
            'operator_join', {'STRING1': "join(vars.x, ';', vars.y)",
                              'STRING2': "join('a', 'b')"}, {}, {},
            'Stage', as_command=False,
        )
        assert source == "join(vars.x, ';', vars.y, join('a', 'b'))"


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
            assert source is not None
            assert isinstance(eval(source, {'Arithmetic': Arithmetic, 'Comparison': Comparison}), expected)


def test_imported_arithmetic_uses_operators_with_text_variables(tmp_path):
    from types import SimpleNamespace
    from itchy.game import String
    project = {'targets': [{'isStage': True, 'name': 'Stage', 'blocks': {}}]}
    with ZipFile(BytesIO(), 'w') as archive:
        importer = PythonImporter(Path('test.sb3'), project, archive, tmp_path)
        source = importer._semantic_block(
            'operator_divide', {'NUM1': '100', 'NUM2': 'vars.zoom'}, {}, {},
            'Stage', as_command=False,
        )
        assert source == '(100 / vars.zoom)'
        variables = SimpleNamespace(zoom=String('zoom', '10'))
        assert source is not None
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
        single = "(if_(b).then_((move_x(2),)).else_((move_x(3),)),)"
        source = importer._semantic_block('control_if_else', {'CONDITION': 'a'}, {},
                                         {'SUBSTACK': '(move_x(1),)', 'SUBSTACK2': single},
                                         'Stage', as_command=False)
        assert source is not None
        assert '.elif_(b)' in source
        assert '.else_((move_x(3),))' in source
        multiple = '(if_(b).then_((move_x(2),)), move_x(4))'
        source = importer._semantic_block('control_if_else', {'CONDITION': 'a'}, {},
                                         {'SUBSTACK': '(move_x(1),)', 'SUBSTACK2': multiple},
                                         'Stage', as_command=False)
        assert source is not None
        assert '.elif_' not in source


def test_import_splits_sprite_modules_and_scopes_variables(tmp_path):
    import json
    import subprocess
    import sys
    from itchy.importer import import_project
    project = {'targets': [
        {'isStage': True, 'name': 'Stage', 'variables': {'global': ['score', 0]},
         'blocks': {}, 'lists': {'path': ['WalkX', [1, 2]]}, 'broadcasts': {'start': 'start'}},
        {'isStage': False, 'name': 'Player', 'variables': {'local': ['health', 10]},
         'lists': {'inventory': ['inventory', []]}, 'blocks': {
             'hat': {'opcode': 'event_whenflagclicked', 'topLevel': True, 'next': 'set'},
             'set': {'opcode': 'data_setvariableto', 'next': None,
                     'fields': {'VARIABLE': ['health', 'local']},
                     'inputs': {'VALUE': [3, [12, 'score', 'global'], [10, '']]}}
         }, 'costumes': []},
    ]}
    project['monitors'] = [{'id': 'path', 'opcode': 'data_listcontents', 'params': {'LIST': 'WalkX'}, 'mode': 'list', 'x': 12, 'visible': False}]
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
    assert not (directory / 'shared.py').exists()
    assert 'Monitor(lists.WalkX, x=12)' in (directory / 'game.py').read_text()
    assert 'score = Num(' in (directory / 'vars.py').read_text()
    assert 'WalkX = ScratchList(' in (directory / 'lists.py').read_text()
    assert 'inventory' not in (directory / 'lists.py').read_text()
    assert 'inventory = ScratchList(' in sprite
    assert 'start = Message(' in (directory / 'messages.py').read_text()
    assert 'lists.WalkX' in (directory / 'game.py').read_text()
    assert 'messages.start' in (directory / 'game.py').read_text()
    for module in ('vars.py', 'lists.py', 'messages.py', 'sprite_player.py'):
        assert 'id=' not in (directory / module).read_text()
    subprocess.run([sys.executable, '-c',
                    'from pathlib import Path; from itchy.project import load_game; '
                    'from itchy.compiler import compile_game; '
                    f'compile_game(load_game(Path({str(directory)!r})))'], check=True)
