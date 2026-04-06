# ============================================================================
# MODULE: nlu (L1 — Natural Language Understanding)
# ============================================================================
#
# This package contains the NLU pipeline that processes raw user messages
# before they reach the agent orchestrator. It classifies intent, extracts
# entities, and resolves ambiguity.
#
# Files in this package:
#   - intent_classifier.py  → Classify domain and intent from raw text
#   - entity_extractor.py   → Extract dates, names, topics, etc.
#   - ambiguity_resolver.py → Detect and resolve underspecified commands
# ============================================================================
