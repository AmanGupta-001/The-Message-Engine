"""
generate_submission.py - Generates the canonical submission.jsonl covering all 30 test pairs.
Uses composer.py to build deterministic, verifiable, zero-hallucination compositions.
"""

import json
from pathlib import Path
from composer import compose

def main():
    expanded_dir = Path("expanded")
    test_pairs_path = expanded_dir / "test_pairs.json"
    
    if not test_pairs_path.exists():
        print("expanded/test_pairs.json not found! Please run generate_dataset.py first.")
        return
        
    with open(test_pairs_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        pairs = data.get("pairs", [])
        
    print(f"Loaded {len(pairs)} test pairs from test_pairs.json.")
    
    # Preload categories
    categories = {}
    for cat_file in (expanded_dir / "categories").glob("*.json"):
        with open(cat_file, "r", encoding="utf-8") as f:
            cat_data = json.load(f)
            categories[cat_data.get("slug", cat_file.stem)] = cat_data
            
    out_lines = []
    
    for pair in pairs:
        test_id = pair["test_id"]
        tid = pair["trigger_id"]
        mid = pair["merchant_id"]
        cid = pair.get("customer_id")
        
        # Load trigger
        with open(expanded_dir / "triggers" / f"{tid}.json", "r", encoding="utf-8") as f:
            trigger = json.load(f)
            
        # Load merchant
        with open(expanded_dir / "merchants" / f"{mid}.json", "r", encoding="utf-8") as f:
            merchant = json.load(f)
            
        cat_slug = merchant.get("category_slug")
        category = categories.get(cat_slug, {"slug": cat_slug})
        
        # Load customer if present
        customer = None
        if cid:
            with open(expanded_dir / "customers" / f"{cid}.json", "r", encoding="utf-8") as f:
                customer = json.load(f)
                
        # Compose message
        res = compose(category, merchant, trigger, customer)
        
        entry = {
            "test_id": test_id,
            "trigger_id": tid,
            "merchant_id": mid,
            "customer_id": cid,
            "body": res["body"],
            "cta": res["cta"],
            "send_as": res["send_as"],
            "suppression_key": res["suppression_key"],
            "rationale": res["rationale"]
        }
        out_lines.append(entry)
        print(f"[{test_id}] {res['send_as']} | {tid} -> {res['cta']}")
        
    # Write submission.jsonl
    out_path = Path("submission.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for item in out_lines:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"\nSuccessfully wrote {len(out_lines)} lines to {out_path.resolve()}!")

if __name__ == "__main__":
    main()
