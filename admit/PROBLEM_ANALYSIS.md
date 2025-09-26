# 🎯 GRADUATE ADMISSIONS ETL SYSTEM - COMPREHENSIVE PROBLEM ANALYSIS

## 📋 **THE CORE PROBLEM**

We're building an ETL system to extract graduate admissions requirements from university websites. The fundamental challenge is that **universities organize their information in vastly different hierarchical structures**, and we need to discover and extract this information **dynamically** without hardcoding paths or generating fake data.

### **Target Hierarchy:**
```
University → School → Department → Program → Track
    ↓         ↓         ↓          ↓        ↓
Stanford → GSB    → Bus Admin  → MBA   → Full-time/Part-time
```

## 🔍 **DISCOVERY CHALLENGE - THE MAIN ISSUE**

### **What We Need to Find:**
- **Real Program Pages**: `https://www.gsb.stanford.edu/programs/mba/admission`
- **Actual Requirements**: TOEFL scores, deadlines, GPA requirements from content
- **Program Variants**: Full-time MBA, Part-time MBA, Executive MBA, PhD, MSx

### **What Our System Currently Finds:**
- **Landing Pages**: `https://www.gsb.stanford.edu/` (homepage)
- **Executive Education**: `https://www.gsb.stanford.edu/exed/` (may not be degree program)
- **Generic Pages**: Limited to 2-3 levels deep

### **The Gap:**
Our discovery system stops at **school homepages** instead of drilling down to find **actual program admission pages**.

## 🛠️ **OUR CURRENT IMPLEMENTATION**

### **ETL Pipeline Architecture:**
1. **Discovery**: `etl/crawler/discover.py` - Find URLs dynamically
2. **Parsing**: `etl/parser/html_segmenter.py` - Extract content from HTML
3. **Extraction**: `etl/extractor/mock_extract.py` - Pull requirements from content
4. **Validation**: `etl/validator/rules.py` - Validate extracted data
5. **Storage**: `etl/storage/database.py` - Store in PostgreSQL

### **Discovery System (Current State):**

#### **Layer 1: Basic Discovery**
- ✅ **Sitemap Parsing**: `robots.txt`, `sitemap.xml`
- ✅ **Homepage Crawling**: Extract links from university homepage
- ✅ **Pattern Testing**: Test common paths like `/admissions`, `/graduate`

#### **Layer 2: School Discovery**
- ✅ **Subdomain Detection**: Find `engineering.stanford.edu`, `gsb.stanford.edu`
- ✅ **Recursive Links**: Extract school URLs from academic pages
- ⚠️ **Shallow Coverage**: Only finds school homepages, not programs within

#### **Layer 3: Multilevel Discovery**
- ⚠️ **Limited Patterns**: Tests `/programs`, `/admissions` but doesn't crawl them
- ❌ **No Deep Drilling**: Stops at finding `/programs` URL, doesn't crawl it for `/programs/mba`

## ❌ **SPECIFIC FAILURES**

### **Stanford GSB Case Study:**
```
❌ MISSED: /programs/mba/admission  (Real admission requirements)
❌ MISSED: /programs/phd/admission  (PhD requirements)
❌ MISSED: /programs/msx/admission  (MSx program)
✅ FOUND:  /programs                (Directory page - but not crawled)
✅ FOUND:  /exed                   (Executive education - limited program)
```

### **Why This Matters:**
- **Missing Core Programs**: We're not finding the actual MBA/PhD admission pages
- **Incomplete Requirements**: Homepage content ≠ admission requirements
- **Poor Data Quality**: Generic info instead of specific program requirements

### **Data Quality Issues:**
1. **Mock Data Contamination**: System generates fake TOEFL/GRE requirements
2. **Hardcoded Assumptions**: "Computer Science" department defaults
3. **Missing Citations**: Can't prove where requirements came from
4. **No Real Deadlines**: Despite claiming to extract them

## 🎯 **WHAT WE'VE TRIED**

### **Attempt 1: Hardcoded URL Patterns** ❌
```python
patterns = ['/programs/mba', '/programs/phd', '/programs/msx']
```
**Problem**: Not scalable, university-specific, breaks on different structures

### **Attempt 2: Increased Pattern Coverage** ❌
```python
patterns = ['/programs/mba/admission', '/programs/phd/admission', ...]
```
**Problem**: Still hardcoded, assumes all universities use same URL structure

### **Attempt 3: Mock Data Generation** ❌
```python
# Generated fake TOEFL scores, GRE requirements, deadlines
toefl_min = 100  # FAKE
gre_status = "REQUIRED"  # FAKE
```
**Problem**: Violates core principle - we must only show real extracted data

### **Attempt 4: Dynamic Content Extraction** ⚠️ Partial
```python
def _extract_program_info_from_url(url, segments):
    # Extract from URL patterns and content
```
**Problem**: Still has fallbacks to hardcoded values, doesn't find the right pages

## 🔧 **CURRENT SOLUTION IN PROGRESS**

### **Dynamic Directory Crawling:**
```python
async def _crawl_directory_page(directory_url: str) -> Set[str]:
    """When we find /programs, actually CRAWL it to find /programs/mba"""
    # Parse HTML, find all program links
    # Test each link for admission pages
    # Return all discovered program pages
```

### **How It Should Work:**
1. **Find Directory**: Discover `gsb.stanford.edu/programs`
2. **Crawl Directory**: Parse HTML, extract all program links
3. **Test Admission Pages**: For each program, try `/admission`, `/apply`, `/requirements`
4. **Collect Real URLs**: Build list of actual admission pages
5. **Extract Real Content**: Parse requirements from admission page content

## 🎯 **SUCCESS CRITERIA**

### **Discovery Goals:**
- [ ] Find `gsb.stanford.edu/programs/mba/admission` automatically
- [ ] Find `gsb.stanford.edu/programs/phd/admission` automatically
- [ ] Find `gsb.stanford.edu/programs/msx/admission` automatically
- [ ] Scale to other universities (MIT, CMU, etc.) without hardcoding

### **Extraction Goals:**
- [ ] Extract REAL deadlines from content (not generated)
- [ ] Extract REAL requirements (TOEFL/GRE) with citations to source text
- [ ] Extract program variants (Full-time/Part-time/Executive)
- [ ] NO mock data generation anywhere

### **Data Quality Goals:**
- [ ] 90%+ confidence scores from real content citations
- [ ] Every extracted field linked to actual HTML segment
- [ ] Complete program hierarchy: University → School → Department → Program → Track

## 🚨 **CRITICAL CONSTRAINTS**

### **Never Use Fake Data:**
- ❌ No hardcoded TOEFL scores, deadlines, GPA requirements
- ❌ No generated program names or degree types
- ❌ No mock citations or validation data
- ✅ Empty fields are better than fake fields

### **Scale Without Hardcoding:**
- ❌ No university-specific URL patterns
- ❌ No assumption about directory structures
- ✅ Dynamic discovery that adapts to each university's structure

### **Source Everything:**
- ✅ Every extracted requirement must link to actual HTML content
- ✅ Citations must include actual text snippets, not generated descriptions
- ✅ Confidence scores based on real content analysis, not assumptions

## 📈 **CURRENT STATUS**

### **Working Components:**
- ✅ Basic university homepage discovery (13 URLs from Stanford)
- ✅ School subdomain detection (GSB, Engineering, Medicine, Law)
- ✅ HTML content segmentation and parsing
- ✅ Database schema and storage system
- ✅ Validation framework with confidence scoring

### **Major Gaps:**
- ❌ **Deep Program Discovery**: Stops at school level, doesn't find program pages
- ❌ **Real Requirements Extraction**: Still generating mock data
- ❌ **Deadline Parsing**: Regex patterns exist but not finding real deadlines
- ❌ **Program Variant Detection**: Missing Full-time vs Part-time tracks

### **Next Steps:**
1. **Test Deep Crawling**: Run Stanford with new `_crawl_directory_page` logic
2. **Remove Mock Data**: Replace all fake generation with real content extraction
3. **Add Citation Validation**: Ensure every requirement has real HTML source
4. **Scale Testing**: Verify approach works across MIT, CMU, other universities

## 💡 **THE PATH FORWARD**

### **Technical Strategy:**
1. **Layer-by-Layer Discovery**: University → Schools → Departments → Programs → Tracks
2. **Dynamic Content Crawling**: Parse directory pages to find actual program links
3. **Real Content Extraction**: Only extract what we can verify from HTML segments
4. **Comprehensive Citation**: Link every data point to source text

### **Success Metric:**
When we can run `python run_etl.py stanford` and see:
```
✅ Found: https://www.gsb.stanford.edu/programs/mba/admission
✅ Extracted: Application deadline January 5, 2025 (cited from HTML)
✅ Extracted: GMAT/GRE optional for 2025 (cited from HTML)
✅ Programs: MBA Full-time, MBA Part-time, PhD, MSx (all with real admission pages)
```

That's when we'll know the system truly works.