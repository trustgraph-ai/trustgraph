# tg-show-token-costs

Displays token cost configuration for language models in TrustGraph.

## Synopsis

```bash
tg-show-token-costs [options]
```

## Description

The `tg-show-token-costs` command displays the configured token pricing for all language models in TrustGraph. This information shows input and output costs per million tokens, which is used for cost tracking, billing, and resource management.

The costs are displayed in a tabular format showing model names and their associated pricing in dollars per million tokens.

## Options

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Display All Token Costs
```bash
tg-show-token-costs
```

### Using Custom API URL
```bash
tg-show-token-costs -u http://production:8088/
```

## Output Format

The command displays costs in a formatted table:

```
+----------------+-------------+--------------+
| model          | input, $/Mt | output, $/Mt |
+----------------+-------------+--------------+
| gpt-4          |      30.000 |       60.000 |
| gpt-3.5-turbo  |       0.500 |        1.500 |
| claude-3-sonnet|       3.000 |       15.000 |
| claude-3-haiku |       0.250 |        1.250 |
| local-model    |       0.000 |        0.000 |
+----------------+-------------+--------------+
```

### Column Details

- **model**: Language model identifier
- **input, $/Mt**: Cost per million input tokens in USD
- **output, $/Mt**: Cost per million output tokens in USD

### Missing Configuration

If a model has incomplete cost configuration:
```
+----------------+-------------+--------------+
| model          | input, $/Mt | output, $/Mt |
+----------------+-------------+--------------+
| unconfigured   |           - |            - |
+----------------+-------------+--------------+
```

## Use Cases

### Cost Monitoring
```bash
# Check current cost configuration
tg-show-token-costs

# Monitor costs over time
echo "$(date): $(tg-show-token-costs)" >> cost_history.log
```

### Cost Analysis
```bash
# Find most expensive models
tg-show-token-costs | grep -v "model" | sort -k3 -nr

# Find free/local models
tg-show-token-costs | grep "0.000"
```

### Budget Planning
```bash
# Calculate potential costs for usage scenarios
analyze_costs() {
  echo "Cost Analysis for Usage Scenarios"
  echo "================================="
  
  # Extract cost data
  tg-show-token-costs | grep -v "model" | \
    while read -r line; do
      model=$(echo "$line" | awk '{print $1}' | tr -d '|' | tr -d ' ')
      input_cost=$(echo "$line" | awk '{print $2}' | tr -d '|' | tr -d ' ')
      output_cost=$(echo "$line" | awk '{print $3}' | tr -d '|' | tr -d ' ')
      
      if [[ "$input_cost" != "-" && "$output_cost" != "-" ]]; then
        echo "Model: $model"
        echo "  1M input tokens: \$${input_cost}"
        echo "  1M output tokens: \$${output_cost}"
        echo "  10K conversation (5K in/5K out): \$$(echo "scale=3; ($input_cost * 5 + $output_cost * 5) / 1000" | bc -l)"
        echo ""
      fi
    done
}

analyze_costs
```

### Environment Comparison
```bash
# Compare costs across environments
compare_costs() {
  local env1_url="$1"
  local env2_url="$2"
  
  echo "Cost Comparison"
  echo "==============="
  echo "Environment 1: $env1_url"
  tg-show-token-costs -u "$env1_url"
  
  echo ""
  echo "Environment 2: $env2_url"
  tg-show-token-costs -u "$env2_url"
}

compare_costs "http://dev:8088/" "http://prod:8088/"
```

## Advanced Usage

### Cost Reporting
```bash
# Generate detailed cost report
generate_cost_report() {
  local report_file="token_costs_$(date +%Y%m%d_%H%M%S).txt"
  
  echo "TrustGraph Token Cost Report" > "$report_file"
  echo "Generated: $(date)" >> "$report_file"
  echo "============================" >> "$report_file"
  echo "" >> "$report_file"
  
  tg-show-token-costs >> "$report_file"
  
  echo "" >> "$report_file"
  echo "Cost Analysis:" >> "$report_file"
  echo "==============" >> "$report_file"
  
  # Add cost analysis
  total_models=$(tg-show-token-costs | grep -c "|" | awk '{print $1-3}')  # Subtract header rows
  free_models=$(tg-show-token-costs | grep -c "0.000")
  paid_models=$((total_models - free_models))
  
  echo "Total models configured: $total_models" >> "$report_file"
  echo "Paid models: $paid_models" >> "$report_file"
  echo "Free models: $free_models" >> "$report_file"
  
  # Find most expensive models
  echo "" >> "$report_file"
  echo "Most expensive models (by output cost):" >> "$report_file"
  tg-show-token-costs | grep -v "model" | grep -v "^\+" | \
    sort -k3 -nr | head -3 >> "$report_file"
  
  echo "Report saved: $report_file"
}

generate_cost_report
```

### Cost Validation
```bash
# Validate cost configuration
validate_cost_config() {
  echo "Cost Configuration Validation"
  echo "============================="
  
  local issues=0
  
  # Check for unconfigured models
  unconfigured=$(tg-show-token-costs | grep -c "\-")
  if [ "$unconfigured" -gt 0 ]; then
    echo "⚠ Warning: $unconfigured models have incomplete cost configuration"
    tg-show-token-costs | grep "\-"
    issues=$((issues + 1))
  fi
  
  # Check for zero-cost models (might be intentional)
  zero_cost=$(tg-show-token-costs | grep -c "0.000.*0.000")
  if [ "$zero_cost" -gt 0 ]; then
    echo "ℹ Info: $zero_cost models configured with zero cost (likely local models)"
  fi
  
  # Check for unusual cost patterns
  tg-show-token-costs | grep -v "model" | grep -v "^\+" | \
    while read -r line; do
      input_cost=$(echo "$line" | awk '{print $2}' | tr -d '|' | tr -d ' ')
      output_cost=$(echo "$line" | awk '{print $3}' | tr -d '|' | tr -d ' ')
      model=$(echo "$line" | awk '{print $1}' | tr -d '|' | tr -d ' ')
      
      if [[ "$input_cost" != "-" && "$output_cost" != "-" ]]; then
        # Check if output cost is lower than input cost (unusual)
        if (( $(echo "$output_cost < $input_cost" | bc -l) )); then
          echo "⚠ Warning: $model has output cost lower than input cost"
          issues=$((issues + 1))
        fi
        
        # Check for extremely high costs
        if (( $(echo "$input_cost > 100" | bc -l) )) || (( $(echo "$output_cost > 200" | bc -l) )); then
          echo "⚠ Warning: $model has unusually high costs"
          issues=$((issues + 1))
        fi
      fi
    done
  
  if [ "$issues" -eq 0 ]; then
    echo "✓ Cost configuration appears valid"
  else
    echo "Found $issues potential issues"
  fi
}

validate_cost_config
```

### Cost Tracking
```bash
# Track cost changes over time
track_cost_changes() {
  local history_file="cost_history.txt"
  local current_file="current_costs.tmp"
  
  # Get current costs
  tg-show-token-costs > "$current_file"
  
  # Check if this is first run
  if [ ! -f "$history_file" ]; then
    echo "$(date): Initial cost configuration" >> "$history_file"
    cat "$current_file" >> "$history_file"
    echo "---" >> "$history_file"
  else
    # Compare with last known state
    if ! diff -q "$history_file" "$current_file" > /dev/null 2>&1; then
      echo "$(date): Cost configuration changed" >> "$history_file"
      
      # Show differences
      echo "Changes:" >> "$history_file"
      diff "$history_file" "$current_file" | tail -n +1 >> "$history_file"
      
      echo "New configuration:" >> "$history_file"
      cat "$current_file" >> "$history_file"
      echo "---" >> "$history_file"
      
      echo "Cost changes detected and logged to $history_file"
    else
      echo "No cost changes detected"
    fi
  fi
  
  rm "$current_file"
}

track_cost_changes
```

### Export Cost Data
```bash
# Export costs to CSV
export_costs_csv() {
  local output_file="$1"
  
  echo "model,input_cost_per_million,output_cost_per_million" > "$output_file"
  
  tg-show-token-costs | grep -v "model" | grep -v "^\+" | \
    while read -r line; do
      model=$(echo "$line" | awk '{print $1}' | tr -d '|' | tr -d ' ')
      input_cost=$(echo "$line" | awk '{print $2}' | tr -d '|' | tr -d ' ')
      output_cost=$(echo "$line" | awk '{print $3}' | tr -d '|' | tr -d ' ')
      
      if [[ "$model" != "" ]]; then
        echo "$model,$input_cost,$output_cost" >> "$output_file"
      fi
    done
  
  echo "Costs exported to: $output_file"
}

# Export to CSV
export_costs_csv "token_costs.csv"

# Export to JSON
export_costs_json() {
  local output_file="$1"
  
  echo "{" > "$output_file"
  echo "  \"export_date\": \"$(date -Iseconds)\"," >> "$output_file"
  echo "  \"models\": [" >> "$output_file"
  
  first=true
  tg-show-token-costs | grep -v "model" | grep -v "^\+" | \
    while read -r line; do
      model=$(echo "$line" | awk '{print $1}' | tr -d '|' | tr -d ' ')
      input_cost=$(echo "$line" | awk '{print $2}' | tr -d '|' | tr -d ' ')
      output_cost=$(echo "$line" | awk '{print $3}' | tr -d '|' | tr -d ' ')
      
      if [[ "$model" != "" ]]; then
        if [ "$first" = "false" ]; then
          echo "," >> "$output_file"
        fi
        first=false
        
        echo "    {" >> "$output_file"
        echo "      \"model\": \"$model\"," >> "$output_file"
        echo "      \"input_cost\": \"$input_cost\"," >> "$output_file"
        echo "      \"output_cost\": \"$output_cost\"" >> "$output_file"
        echo -n "    }" >> "$output_file"
      fi
    done
  
  echo "" >> "$output_file"
  echo "  ]" >> "$output_file"
  echo "}" >> "$output_file"
  
  echo "Costs exported to: $output_file"
}

export_costs_json "token_costs.json"
```

### Cost Calculation Tools
```bash
# Calculate costs for usage scenarios
calculate_usage_cost() {
  local model="$1"
  local input_tokens="$2"
  local output_tokens="$3"
  
  echo "Calculating cost for $model usage:"
  echo "  Input tokens: $input_tokens"
  echo "  Output tokens: $output_tokens"
  
  # Extract costs for specific model
  costs=$(tg-show-token-costs | grep "$model")
  
  if [ -z "$costs" ]; then
    echo "Error: Model $model not found in cost configuration"
    return 1
  fi
  
  input_cost=$(echo "$costs" | awk '{print $2}' | tr -d '|' | tr -d ' ')
  output_cost=$(echo "$costs" | awk '{print $3}' | tr -d '|' | tr -d ' ')
  
  if [[ "$input_cost" == "-" || "$output_cost" == "-" ]]; then
    echo "Error: Incomplete cost configuration for $model"
    return 1
  fi
  
  # Calculate total cost
  total_cost=$(echo "scale=6; ($input_tokens * $input_cost / 1000000) + ($output_tokens * $output_cost / 1000000)" | bc -l)
  
  echo "  Input cost: \$$(echo "scale=6; $input_tokens * $input_cost / 1000000" | bc -l)"
  echo "  Output cost: \$$(echo "scale=6; $output_tokens * $output_cost / 1000000" | bc -l)"
  echo "  Total cost: \$${total_cost}"
}

# Example usage calculations
calculate_usage_cost "gpt-4" 1000 500
calculate_usage_cost "claude-3-sonnet" 5000 2000
```

### Model Cost Comparison
```bash
# Compare costs across models for same usage
compare_model_costs() {
  local input_tokens="${1:-1000}"
  local output_tokens="${2:-500}"
  
  echo "Cost comparison for $input_tokens input + $output_tokens output tokens:"
  echo "====================================================================="
  
  tg-show-token-costs | grep -v "model" | grep -v "^\+" | \
    while read -r line; do
      model=$(echo "$line" | awk '{print $1}' | tr -d '|' | tr -d ' ')
      input_cost=$(echo "$line" | awk '{print $2}' | tr -d '|' | tr -d ' ')
      output_cost=$(echo "$line" | awk '{print $3}' | tr -d '|' | tr -d ' ')
      
      if [[ "$model" != "" && "$input_cost" != "-" && "$output_cost" != "-" ]]; then
        total_cost=$(echo "scale=4; ($input_tokens * $input_cost / 1000000) + ($output_tokens * $output_cost / 1000000)" | bc -l)
        printf "%-20s \$%s\n" "$model" "$total_cost"
      fi
    done | sort -k2 -n
}

# Compare costs for typical usage
compare_model_costs 1000 500
```

## Error Handling

### Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Check API URL and ensure TrustGraph is running.

### Permission Errors
```bash
Exception: Access denied
```
**Solution**: Verify user permissions for configuration access.

### No Models Configured
```bash
# Empty table or no data
```
**Solution**: Configure model costs with `tg-set-token-costs`.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-set-token-costs`](tg-set-token-costs.md) - Configure token costs
- [`tg-show-config`](tg-show-config.md) - Show other configuration settings (if available)

## API Integration

This command uses the [Config API](../apis/api-config.md) to retrieve token cost configuration from TrustGraph's configuration system.

## Best Practices

1. **Regular Review**: Check cost configurations regularly
2. **Cost Tracking**: Monitor cost changes over time
3. **Validation**: Validate cost configurations for accuracy
4. **Documentation**: Document cost sources and update procedures
5. **Reporting**: Generate regular cost reports for budget planning
6. **Comparison**: Compare costs across environments
7. **Automation**: Automate cost monitoring and alerting

## Troubleshooting

### Missing Cost Data
```bash
# Check if models are configured
tg-show-token-costs | grep -c "model"

# Verify specific model exists
tg-show-token-costs | grep "model-name"
```

### Formatting Issues
```bash
# If table is garbled
export COLUMNS=120
tg-show-token-costs
```

### Incomplete Data
```bash
# Look for models with missing costs
tg-show-token-costs | grep "\-"

# Set missing costs
tg-set-token-costs --model "incomplete-model" -i 1.0 -o 2.0
```