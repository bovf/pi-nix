"""Installed SDK boundary: expected validation is not an unexpected tool crash."""
import asyncio
from unittest.mock import patch

from main import serve
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError


class EngineFixture:
    def __init__(self):
        self.privacy_calls = []

    def create(self, project):
        if project == 'denied':
            raise ValueError('synthetic expected refusal')
        if project == 'crash':
            raise RuntimeError('synthetic invariant failure')
        return {'project': project}

    def privacy(self, project, allow_remote):
        self.privacy_calls.append((project, allow_remote))
        return {'allow_remote': allow_remote}


async def check():
    captured = []
    engine = EngineFixture()
    with patch.object(MCPServer, 'run', lambda server, **_kwargs: captured.append(server)):
        serve(engine)
    assert len(captured) == 1
    server = captured[0]
    tools = await server.list_tools()
    assert len(tools) == 38 and len({tool.name for tool in tools}) == 38
    catalog = {tool.name: tool for tool in tools}
    assert catalog['project_create'].input_schema['required'] == ['project']
    assert catalog['project_privacy'].input_schema['properties']['allow_remote']['type'] == 'boolean'
    assert 'USER permission' in catalog['project_privacy'].description
    assert await server.call_tool('project_create', {'project': 'valid'})
    for project, expected in [('denied', ToolError), ('crash', UnexpectedToolError)]:
        try:
            await server.call_tool('project_create', {'project': project})
            raise AssertionError('expected refusal/crash was accepted')
        except ToolError as exc:
            assert type(exc) is expected, (project, type(exc))
            if project == 'denied':
                assert 'synthetic expected refusal' in str(exc)
            else:
                assert 'synthetic invariant failure' not in str(exc)
                assert isinstance(exc.__cause__, RuntimeError)
    for malformed in ['true', 1, None]:
        try:
            await server.call_tool('project_privacy', {'project': 'valid', 'allow_remote': malformed})
            raise AssertionError('nonboolean consent reached the engine')
        except ToolError as exc:
            assert not isinstance(exc, UnexpectedToolError)
    assert not engine.privacy_calls
    await server.call_tool('project_privacy', {'project': 'valid', 'allow_remote': True})
    assert engine.privacy_calls == [('valid', True)]
    print('PASS 38 installed tool registrations/signatures/docs; expected ValueError -> ToolError; unexpected RuntimeError remains crash; consent remains strict boolean')


asyncio.run(check())
