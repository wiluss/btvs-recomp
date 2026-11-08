import unittest
from unittest.mock import Mock
from tools.local_ai import Client, context_file, probe, ask


class LocalBridgeTests(unittest.TestCase):
    def test_reasoning_without_final_answer_is_not_success(self):
        client = Mock()
        client.request.return_value = {'choices':[{'message':{'content':''}}],
                                       'usage':{'completion_tokens':3000}}
        with self.assertRaisesRegex(ValueError, 'no final answer'):
            ask(client, 'synthetic-model', 'Tiny review', [], 3000)

    def test_empty_answer_reports_budget_evidence(self):
        client = Mock()
        client.request.return_value = {
            'choices':[{'message':{'content':None}, 'finish_reason':'length'}],
            'usage':{'completion_tokens':2048,
                     'completion_tokens_details':{'reasoning_tokens':2048}}}
        with self.assertRaises(ValueError) as failure:
            ask(client, 'synthetic-model', 'Tiny review', [], 2048)
        message = str(failure.exception)
        self.assertIn("finish_reason='length'", message)
        self.assertIn('completion_tokens=2048', message)
        self.assertIn('reasoning_tokens=2048', message)

    def test_answer_preserves_optional_finish_metadata(self):
        client = Mock()
        for reason in ('stop', 'length', None):
            choice = {'message':{'content':'review'}}
            if reason is not None:
                choice['finish_reason'] = reason
            client.request.return_value = {'choices':[choice],
                                           'usage':{'completion_tokens':20}}
            result = ask(client, 'synthetic-model', 'Tiny review', [], 100)
            self.assertEqual(result, {'answer':'review',
                                     'usage':{'completion_tokens':20},
                                     'finish_reason':reason})

    def test_loopback_only(self):
        for url in ('https://example.com/v1','http://127.0.0.1.evil/v1',
                    'http://localhost/v1?redirect=x','http://user:pass@localhost/v1'):
            with self.assertRaises(ValueError): Client(url)
        Client('http://127.0.0.1:1234/v1')

    def test_context_boundary(self):
        for path in ('../../secret.txt', 'private/game/Default.xbe', '.git/config'):
            with self.assertRaises(ValueError): context_file(path)

    def test_tool_round_trip_without_execution(self):
        client = Mock()
        client.request.side_effect = [
            {'choices':[{'message':{'content':None,'tool_calls':[{
                'id':'test-1','type':'function',
                'function':{'name':'read_fixture','arguments':'{"name":"buffy_probe"}'}}]}}]},
            {'choices':[{'message':{'content':'LOCAL_BUFFY_OK'}}]},
        ]
        self.assertTrue(probe(client, 'synthetic-model')['passed'])
        self.assertEqual(client.request.call_count,2)
        second = client.request.call_args.args[1]
        self.assertEqual(second['messages'][-1]['tool_call_id'],'test-1')

    def test_wrong_tool_rejected(self):
        client = Mock()
        client.request.return_value = {'choices':[{'message':{'tool_calls':[{
            'id':'bad','type':'function','function':{'name':'shell','arguments':'{}'}}]}}]}
        with self.assertRaises(ValueError): probe(client,'synthetic-model')
        self.assertEqual(client.request.call_count,1)


if __name__ == '__main__': unittest.main()
