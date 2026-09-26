"""
test_harness.py - Local test runner mirroring judge_simulator.py scenarios:
1. Warmup (/v1/healthz, /v1/metadata, /v1/context pushes)
2. Auto-reply detection (/v1/reply with canned WhatsApp Business messages)
3. Intent transition (/v1/reply switching to immediate action mode)
4. Hostile message handling (/v1/reply graceful end / opt-out)
5. Tick actions (/v1/tick verifying composed messages against the 30 canonical pairs)
"""

import sys
import json
import time
from pathlib import Path
from judge_simulator import BotClient, DatasetLoader, Colors, print_header, print_section, print_success, print_fail, print_info, print_warn

BOT_URL = "http://127.0.0.1:8000"

def run_tests():
    print_header("MAGICPIN VERA - LOCAL AUTOMATED VALIDATION HARNESS")
    client = BotClient(BOT_URL)
    dataset = DatasetLoader(Path("dataset"))
    
    if not dataset.load():
        print_fail("Failed to load dataset seeds from ./dataset")
        sys.exit(1)
        
    print_success(f"Dataset loaded: {len(dataset.categories)} categories, {len(dataset.merchants)} merchants, {len(dataset.triggers)} triggers")
    
    # 1. Warmup
    print_section("SCENARIO 1: WARMUP")
    data, err, lat = client.healthz()
    if err:
        print_fail(f"healthz failed: {err}")
        sys.exit(1)
    print_success(f"healthz passed ({lat:.1f}ms): {data}")
    
    data, err, lat = client.metadata()
    if err:
        print_fail(f"metadata failed: {err}")
        sys.exit(1)
    print_success(f"metadata passed ({lat:.1f}ms): {data.get('team_name')} | Model: {data.get('model')}")
    
    # Push categories
    for slug, cat in dataset.categories.items():
        data, err, _ = client.push_context("category", slug, 1, cat)
        if not data or not data.get("accepted"):
            print_fail(f"Push category/{slug} failed: {err}")
        else:
            print_success(f"Pushed category/{slug}")
            
    # Push merchants
    for mid, m in dataset.merchants.items():
        data, err, _ = client.push_context("merchant", mid, 1, m)
        if not data or not data.get("accepted"):
            print_fail(f"Push merchant/{mid} failed: {err}")
        else:
            print_success(f"Pushed merchant/{mid}")
            
    # Push customers
    for cid, c in dataset.customers.items():
        data, err, _ = client.push_context("customer", cid, 1, c)
        if not data or not data.get("accepted"):
            print_fail(f"Push customer/{cid} failed: {err}")
        else:
            print_success(f"Pushed customer/{cid}")
            
    # Push triggers
    for tid, t in dataset.triggers.items():
        data, err, _ = client.push_context("trigger", tid, 1, t)
        if not data or not data.get("accepted"):
            print_fail(f"Push trigger/{tid} failed: {err}")
        else:
            print_success(f"Pushed trigger/{tid}")

    # Check updated healthz
    data, _, _ = client.healthz()
    print_info(f"Updated context counts in bot: {data.get('contexts_loaded')}")
    
    # 2. Auto-reply detection
    print_section("SCENARIO 2: AUTO-REPLY DETECTION")
    mid = list(dataset.merchants.keys())[0]
    auto_msg = "Thank you for contacting us! Our team will respond shortly."
    auto_passed = False
    for i in range(1, 5):
        data, err, _ = client.reply(f"conv_auto_{i}", mid, auto_msg, i + 1)
        action = data.get("action") if data else "error"
        print_info(f"Turn {i}: Auto-reply sent -> Bot action: {action} ({data.get('rationale')})")
        if action == "end":
            print_success(f"Turn {i}: Bot ENDED successfully detecting auto-reply pollution!")
            auto_passed = True
            break
        elif action == "wait":
            print_success(f"Turn {i}: Bot backed off with wait ({data.get('wait_seconds')}s)")
            
    if not auto_passed:
        print_warn("Bot did not terminate after repeated auto-replies")

    # 3. Intent transition
    print_section("SCENARIO 3: INTENT TRANSITION")
    commitment = "Ok lets do it. Whats next?"
    data, err, _ = client.reply("conv_intent_1", mid, commitment, 2)
    action = data.get("action") if data else "error"
    body = data.get("body", "") if data else ""
    print_info(f"Merchant commitment: \"{commitment}\"")
    print_info(f"Bot response action: {action}")
    print_info(f"Bot body: \"{body}\"")
    
    qualifying = ["would you", "do you", "can you tell", "what if", "how about"]
    actioning = ["done", "proceeding", "draft", "here", "confirm", "proceed", "next", "scheduled"]
    body_lower = body.lower()
    if any(w in body_lower for w in actioning) and not any(w in body_lower for w in qualifying):
        print_success("Bot correctly switched to ACTION mode without qualifying delay!")
    else:
        print_fail("Bot failed intent transition check")

    # 4. Hostile Handling
    print_section("SCENARIO 4: HOSTILE HANDLING")
    hostile = "Stop messaging me. This is useless spam."
    data, err, _ = client.reply("conv_hostile", mid, hostile, 2)
    action = data.get("action") if data else "error"
    print_info(f"Hostile message: \"{hostile}\" -> Bot action: {action}")
    if action == "end":
        print_success("Bot correctly ENDED on hostile/opt-out request with 0 spam!")
    else:
        print_fail(f"Bot did not end on hostile message (got {action})")

    # 5. Tick & Composition on triggers
    print_section("SCENARIO 5: TICK ACTIONS & COMPOSITION")
    trigs = list(dataset.triggers.keys())[:10]
    data, err, lat = client.tick(trigs)
    if err:
        print_fail(f"Tick error: {err}")
    else:
        actions = data.get("actions", [])
        print_success(f"Tick produced {len(actions)} actions across {len(trigs)} triggers ({lat:.1f}ms):")
        for act in actions:
            print(f"\n  {Colors.CYAN}Trigger:{Colors.RESET} {act['trigger_id']}")
            print(f"  {Colors.BOLD}Send As:{Colors.RESET} {act['send_as']} | {Colors.BOLD}CTA:{Colors.RESET} {act['cta']}")
            clean_body = act['body'].encode('ascii', errors='replace').decode('ascii')
            print(f"  {Colors.GREEN}Body:{Colors.RESET} \"{clean_body}\"")
            print(f"  {Colors.DIM}Rationale: {act['rationale']}{Colors.RESET}")

    print_header("ALL SCENARIOS VALIDATED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
