import sys
sys.path.insert(0, r'C:\Users\kevin\Desktop\mcop-arc-agent\mcop-source\mcop_package')

import argparse
import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict

from mcop.triad import nova_neo_encode

class MCOP_ARC_Agent_v2:
    def __init__(self):
        self.provenance_log = []
        self.xai_key = os.getenv('XAI_API_KEY')

    def act(self, observation: str, step: int) -> Dict[str, Any]:
        tensor = nova_neo_encode(observation, dimensions=64)

        action = {'action': 'probe'}
        if self.xai_key:
            try:
                data = json.dumps({
                    'model': 'grok-3-mini',
                    'messages': [{'role': 'user', 'content': f'Step {step}: {observation[:200]}. Return ONLY JSON: {{"action": "..."}}'}],
                    'temperature': 0.0,
                    'response_format': {'type': 'json_object'}
                }).encode('utf-8')

                req = urllib.request.Request(
                    'https://api.x.ai/v1/chat/completions',
                    data=data,
                    headers={'Authorization': f'Bearer {self.xai_key}', 'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=60) as resp:   # increased timeout
                    result = json.loads(resp.read().decode())
                    content = result['choices'][0]['message']['content']
                    action = json.loads(content)
                print(f'✅ Grok responded at step {step}')
            except Exception as e:
                print(f'⚠️ Grok call failed: {e}')

        self.provenance_log.append({
            'step': step,
            'observation': observation[:100],
            'tensor_length': len(tensor),
            'action': action
        })
        return action

    def save_provenance(self, task_id: str):
        os.makedirs('provenance', exist_ok=True)
        with open(f'provenance/mcop_provenance_{task_id}.json', 'w') as f:
            json.dump({
                'framework': 'MCOP-Framework-2.0 + Real Grok',
                'task_id': task_id,
                'events': self.provenance_log
            }, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--game', type=str, default='ls20')
    args = parser.parse_args()

    print(f'🚀 Running MCOP-Framework-2.0 + Real Grok on game: {args.game}')

    agent = MCOP_ARC_Agent_v2()

    for step in range(20):   # reduced to 20 steps for faster testing
        obs = f'Mock ARC-AGI-3 observation step {step}'
        agent.act(obs, step)

    agent.save_provenance(args.game)

    print('✅ Run complete!')
    print(f'   Provenance saved: provenance/mcop_provenance_{args.game}.json')

if __name__ == '__main__':
    main()
