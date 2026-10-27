#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
print('AVAILABLE MODELS:')
print('='*100)

for m in data['data']:
    print(f"\n{m['id']}")
    ctx = m.get('context_window_tokens')
    max_out = m.get('maximum_output_tokens')
    print(f"  Context: {ctx:,} tokens" if ctx else "  Context: N/A")
    print(f"  Max Output: {max_out:,} tokens" if max_out else "  Max Output: N/A")
    
    pricing = m.get('pricing', {})
    input_cost = pricing.get('input_nano_usd_per_million_tokens')
    output_cost = pricing.get('output_nano_usd_per_million_tokens')
    
    if input_cost and output_cost:
        input_usd = input_cost / 1_000_000_000
        output_usd = output_cost / 1_000_000_000
        print(f"  Cost: ${input_usd:.3f} in / ${output_usd:.3f} out per 1M tokens")
    else:
        print(f"  Cost: Free or pricing not shown")
    
    features = []
    if m.get('supports_tools'): features.append('tools')
    if m.get('emits_images'): features.append('image-gen')
    if m.get('supports_structured_output'): features.append('structured')
    if m.get('supports_reasoning'): features.append('reasoning')
    print(f"  Features: {', '.join(features) if features else 'basic'}")
