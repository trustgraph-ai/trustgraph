# tg-invoke-document-rag

Invokes the DocumentRAG service to answer questions using document context and retrieval-augmented generation.

## Synopsis

```bash
tg-invoke-document-rag -q QUESTION [options]
```

## Description

The `tg-invoke-document-rag` command uses TrustGraph's DocumentRAG service to answer questions by retrieving relevant document context and generating responses using large language models. This implements a Retrieval-Augmented Generation (RAG) approach that grounds AI responses in your document corpus.

The service searches through indexed documents to find relevant context, then uses that context to generate accurate, source-backed answers to questions.

## Options

### Required Arguments

- `-q, --question QUESTION`: The question to answer

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-f, --flow-id ID`: Flow instance ID to use (default: `default`)
- `-U, --user USER`: User ID for context isolation (default: `trustgraph`)
- `-C, --collection COLLECTION`: Document collection to search (default: `default`)
- `-d, --doc-limit LIMIT`: Maximum number of documents to retrieve (default: `10`)

## Examples

### Basic Question Answering
```bash
tg-invoke-document-rag -q "What is the company's return policy?"
```

### Question with Custom Parameters
```bash
tg-invoke-document-rag \
  -q "How do I configure SSL certificates?" \
  -f "production-docs" \
  -U "admin" \
  -C "technical-docs" \
  -d 5
```

### Complex Technical Questions
```bash
tg-invoke-document-rag \
  -q "What are the performance benchmarks for the new API endpoints?" \
  -f "api-docs" \
  -C "performance-reports"
```

### Multi-domain Questions
```bash
# Legal documents
tg-invoke-document-rag -q "What are the privacy policy requirements?" -C "legal-docs"

# Technical documentation
tg-invoke-document-rag -q "How do I troubleshoot connection timeouts?" -C "tech-docs"

# Marketing materials
tg-invoke-document-rag -q "What are our key product differentiators?" -C "marketing"
```

## Output Format

The command returns a structured response with:

```json
{
  "question": "What is the company's return policy?",
  "answer": "Based on the company policy documents, customers can return items within 30 days of purchase for a full refund. Items must be in original condition with receipt. Digital products are non-refundable except in cases of technical defects.",
  "sources": [
    {
      "document": "customer-service-policy.pdf",
      "relevance": 0.92,
      "section": "Returns and Refunds"
    },
    {
      "document": "terms-of-service.pdf", 
      "relevance": 0.85,
      "section": "Customer Rights"
    }
  ],
  "confidence": 0.89
}
```

## Use Cases

### Customer Support
```bash
# Answer common customer questions
tg-invoke-document-rag -q "How do I reset my password?" -C "support-docs"

# Product information queries
tg-invoke-document-rag -q "What are the system requirements?" -C "product-specs"

# Troubleshooting assistance
tg-invoke-document-rag -q "Why is my upload failing?" -C "troubleshooting"
```

### Technical Documentation
```bash
# API documentation queries
tg-invoke-document-rag -q "How do I authenticate with the REST API?" -C "api-docs"

# Configuration questions
tg-invoke-document-rag -q "What are the required environment variables?" -C "config-docs"

# Architecture information
tg-invoke-document-rag -q "How does the caching system work?" -C "architecture"
```

### Research and Analysis
```bash
# Research queries
tg-invoke-document-rag -q "What are the latest industry trends?" -C "research-reports"

# Compliance questions
tg-invoke-document-rag -q "What are the GDPR requirements?" -C "compliance-docs"

# Best practices
tg-invoke-document-rag -q "What are the security best practices?" -C "security-guidelines"
```

### Interactive Q&A Sessions
```bash
# Batch questions for analysis
questions=(
  "What is our market share?"
  "How do we compare to competitors?"
  "What are the growth projections?"
)

for question in "${questions[@]}"; do
  echo "Question: $question"
  tg-invoke-document-rag -q "$question" -C "business-reports"
  echo "---"
done
```

## Document Context and Retrieval

### Document Limit Tuning
```bash
# Few documents for focused answers
tg-invoke-document-rag -q "What is the API rate limit?" -d 3

# Many documents for comprehensive analysis
tg-invoke-document-rag -q "What are all the security measures?" -d 20
```

### Collection-Specific Queries
```bash
# Target specific document collections
tg-invoke-document-rag -q "What is the deployment process?" -C "devops-docs"
tg-invoke-document-rag -q "What are the testing standards?" -C "qa-docs"
tg-invoke-document-rag -q "What is the coding style guide?" -C "dev-standards"
```

### User Context Isolation
```bash
# Department-specific contexts
tg-invoke-document-rag -q "What is the budget allocation?" -U "finance" -C "finance-docs"
tg-invoke-document-rag -q "What are the hiring requirements?" -U "hr" -C "hr-docs"
```

## Error Handling

### Question Required
```bash
Exception: Question is required
```
**Solution**: Provide a question with the `-q` option.

### Flow Not Found
```bash
Exception: Flow instance 'nonexistent-flow' not found
```
**Solution**: Verify the flow ID exists with `tg-show-flows`.

### Collection Not Found
```bash
Exception: Collection 'invalid-collection' not found
```
**Solution**: Check available collections with document library commands.

### No Documents Found
```bash
Exception: No relevant documents found for query
```
**Solution**: Verify documents are indexed and collection contains relevant content.

### API Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Check API URL and ensure TrustGraph services are running.

## Advanced Usage

### Batch Processing
```bash
# Process questions from file
while IFS= read -r question; do
  if [ -n "$question" ]; then
    echo "Processing: $question"
    tg-invoke-document-rag -q "$question" -C "knowledge-base" > "answer-$(date +%s).json"
  fi
done < questions.txt
```

### Question Analysis Pipeline
```bash
#!/bin/bash
# analyze-questions.sh
questions_file="$1"
collection="$2"

if [ -z "$questions_file" ] || [ -z "$collection" ]; then
    echo "Usage: $0 <questions-file> <collection>"
    exit 1
fi

echo "Question Analysis Report - $(date)"
echo "Collection: $collection"
echo "=================================="

question_num=1
while IFS= read -r question; do
    if [ -n "$question" ]; then
        echo -e "\n$question_num. $question"
        echo "$(printf '=%.0s' {1..50})"
        
        # Get answer
        answer=$(tg-invoke-document-rag -q "$question" -C "$collection" 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            echo "$answer" | jq -r '.answer' 2>/dev/null || echo "$answer"
            
            # Extract sources if available
            sources=$(echo "$answer" | jq -r '.sources[]?.document' 2>/dev/null)
            if [ -n "$sources" ]; then
                echo -e "\nSources:"
                echo "$sources" | sed 's/^/  - /'
            fi
        else
            echo "ERROR: Could not get answer"
        fi
        
        question_num=$((question_num + 1))
    fi
done < "$questions_file"
```

### Quality Assessment
```bash
# Assess answer quality with multiple document limits
question="What are the security protocols?"
collection="security-docs"

echo "Answer Quality Assessment"
echo "Question: $question"
echo "========================"

for limit in 3 5 10 15 20; do
    echo -e "\nDocument limit: $limit"
    echo "$(printf '-%.0s' {1..30})"
    
    answer=$(tg-invoke-document-rag -q "$question" -C "$collection" -d $limit 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # Get answer length and source count
        answer_length=$(echo "$answer" | jq -r '.answer' 2>/dev/null | wc -c)
        source_count=$(echo "$answer" | jq -r '.sources | length' 2>/dev/null)
        confidence=$(echo "$answer" | jq -r '.confidence' 2>/dev/null)
        
        echo "Answer length: $answer_length characters"
        echo "Source count: $source_count"
        echo "Confidence: $confidence"
    else
        echo "ERROR: Failed to get answer"
    fi
done
```

### Interactive Q&A Interface
```bash
#!/bin/bash
# interactive-rag.sh
collection="${1:-default}"
flow_id="${2:-default}"

echo "Interactive Document RAG Interface"
echo "Collection: $collection"
echo "Flow ID: $flow_id"
echo "Type 'quit' to exit"
echo "=================================="

while true; do
    echo -n "Question: "
    read -r question
    
    if [ "$question" = "quit" ]; then
        break
    fi
    
    if [ -n "$question" ]; then
        echo "Thinking..."
        answer=$(tg-invoke-document-rag -q "$question" -C "$collection" -f "$flow_id" 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            echo "Answer:"
            echo "$answer" | jq -r '.answer' 2>/dev/null || echo "$answer"
            
            # Show sources if available
            sources=$(echo "$answer" | jq -r '.sources[]?.document' 2>/dev/null)
            if [ -n "$sources" ]; then
                echo -e "\nSources:"
                echo "$sources" | sed 's/^/  - /'
            fi
        else
            echo "Sorry, I couldn't answer that question."
        fi
        
        echo -e "\n$(printf '=%.0s' {1..50})"
    fi
done

echo "Goodbye!"
```

## Performance Optimization

### Document Limit Optimization
```bash
# Test different document limits for performance
question="What is the system architecture?"
collection="tech-docs"

for limit in 3 5 10 15 20; do
    echo "Testing document limit: $limit"
    start_time=$(date +%s%N)
    
    tg-invoke-document-rag -q "$question" -C "$collection" -d $limit > /dev/null 2>&1
    
    end_time=$(date +%s%N)
    duration=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
    
    echo "  Duration: ${duration}ms"
done
```

### Caching Strategy
```bash
# Cache frequently asked questions
cache_dir="rag-cache"
mkdir -p "$cache_dir"

ask_question() {
    local question="$1"
    local collection="$2"
    local cache_key=$(echo "$question-$collection" | md5sum | cut -d' ' -f1)
    local cache_file="$cache_dir/$cache_key.json"
    
    if [ -f "$cache_file" ]; then
        echo "Cache hit for: $question"
        cat "$cache_file"
    else
        echo "Cache miss, querying: $question"
        tg-invoke-document-rag -q "$question" -C "$collection" | tee "$cache_file"
    fi
}

# Use cached queries
ask_question "What is the API documentation?" "tech-docs"
ask_question "What are the system requirements?" "spec-docs"
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-load-pdf`](tg-load-pdf.md) - Load PDF documents for RAG
- [`tg-show-library-documents`](tg-show-library-documents.md) - List available documents
- [`tg-invoke-prompt`](tg-invoke-prompt.md) - Direct prompt invocation without RAG
- [`tg-start-flow`](tg-start-flow.md) - Start flows for document processing
- [`tg-show-flows`](tg-show-flows.md) - List active flow instances

## API Integration

This command uses the [DocumentRAG API](../apis/api-document-rag.md) to perform retrieval-augmented generation using the document corpus.

## Best Practices

1. **Question Formulation**: Use specific, well-formed questions for better results
2. **Collection Organization**: Organize documents into logical collections
3. **Document Limits**: Balance accuracy with performance using appropriate document limits
4. **User Context**: Use user isolation for sensitive or department-specific queries
5. **Source Verification**: Always check source documents for critical information
6. **Caching**: Implement caching for frequently asked questions
7. **Quality Assessment**: Regularly evaluate answer quality and adjust parameters

## Troubleshooting

### Poor Answer Quality
```bash
# Try different document limits
tg-invoke-document-rag -q "your question" -d 5   # Fewer documents
tg-invoke-document-rag -q "your question" -d 15  # More documents

# Check document collection
tg-show-library-documents -C "your-collection"
```

### Slow Response Times
```bash
# Reduce document limit
tg-invoke-document-rag -q "your question" -d 3

# Check flow performance
tg-show-flows | grep "document-rag"
```

### Missing Context
```bash
# Verify documents are indexed
tg-show-library-documents -C "your-collection"

# Check if collection exists
tg-show-library-documents | grep "your-collection"
```