# CRITICAL RULES FOR CLAUDE CODE

## 🚫 NEVER USE FAKE DATA
- NO mock data generation
- NO hardcoded requirements unless absolutely certain they're exhaustive
- NO fake deadlines, scores, or requirements
- If we don't know something from real content, return empty/null
- Only show what we ACTUALLY extracted from real sources

## 🔍 DEEP DISCOVERY REQUIREMENTS
- Discovery must be multi-layered: University → School → Department → Program → Track
- Must find actual program pages like `/programs/mba/admission`, not just landing pages
- Must capture ALL programs at each level before moving to next layer
- Discovery should be exhaustive, not limited to 3-5 URLs

## 🎯 EXTRACTION PRINCIPLES
- Only extract from real content found in HTML segments
- No generation based on URL patterns unless verified in content
- Source everything with citations to actual text segments
- Be honest about what we can/cannot extract reliably