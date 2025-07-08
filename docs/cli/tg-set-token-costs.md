# tg-set-token-costs

Sets token cost configuration for language models in TrustGraph.

## Synopsis

```bash
tg-set-token-costs --model MODEL_ID -i INPUT_COST -o OUTPUT_COST [options]
```

## Description

The `tg-set-token-costs` command configures the token pricing for language models used by TrustGraph. This information is used for cost tracking, billing, and resource management across AI operations.

Token costs are specified in dollars per million tokens and are stored in TrustGraph's configuration system for use by cost monitoring and reporting tools.

## Options

### Required Arguments

- `--model MODEL_ID`: Language model identifier
- `-i, --input-costs COST`: Input token cost in $ per 1M tokens
- `-o, --output-costs COST`: Output token cost in $ per 1M tokens

### Optional Arguments

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)

## Examples

### Set Costs for GPT-4
```bash
tg-set-token-costs \
  --model "gpt-4" \
  -i 30.0 \
  -o 60.0
```

### Set Costs for Claude Sonnet
```bash
tg-set-token-costs \
  --model "claude-3-sonnet" \
  -i 3.0 \
  -o 15.0
```

### Set Costs for Local Model
```bash
tg-set-token-costs \
  --model "llama-2-7b" \
  -i 0.0 \
  -o 0.0
```

### Set Costs with Custom API URL
```bash
tg-set-token-costs \
  --model "gpt-3.5-turbo" \
  -i 0.5 \
  -o 1.5 \
  -u http://production:8088/
```

## Model Pricing Examples

### OpenAI Models (as of 2024)
```bash
# GPT-4 Turbo
tg-set-token-costs --model "gpt-4-turbo" -i 10.0 -o 30.0

# GPT-4
tg-set-token-costs --model "gpt-4" -i 30.0 -o 60.0

# GPT-3.5 Turbo
tg-set-token-costs --model "gpt-3.5-turbo" -i 0.5 -o 1.5
```

### Anthropic Models
```bash
# Claude 3 Opus
tg-set-token-costs --model "claude-3-opus" -i 15.0 -o 75.0

# Claude 3 Sonnet
tg-set-token-costs --model "claude-3-sonnet" -i 3.0 -o 15.0

# Claude 3 Haiku
tg-set-token-costs --model "claude-3-haiku" -i 0.25 -o 1.25
```

### Google Models
```bash
# Gemini Pro
tg-set-token-costs --model "gemini-pro" -i 0.5 -o 1.5

# Gemini Ultra
tg-set-token-costs --model "gemini-ultra" -i 8.0 -o 24.0
```

### Local/Open Source Models
```bash
# Local models typically have no API costs
tg-set-token-costs --model "llama-2-70b" -i 0.0 -o 0.0
tg-set-token-costs --model "mistral-7b" -i 0.0 -o 0.0
tg-set-token-costs --model "local-model" -i 0.0 -o 0.0
```

## Use Cases

### Cost Tracking Setup
```bash
# Set up comprehensive cost tracking
models=(
  "gpt-4:30.0:60.0"
  "gpt-3.5-turbo:0.5:1.5"
  "claude-3-sonnet:3.0:15.0"
  "claude-3-haiku:0.25:1.25"
)

for model_config in "${models[@]}"; do
  IFS=':' read -r model input_cost output_cost <<< "$model_config"
  echo "Setting costs for $model..."
  tg-set-token-costs --model "$model" -i "$input_cost" -o "$output_cost"
done
```

### Environment-Specific Pricing
```bash
# Set different costs for different environments
set_environment_costs() {
  local env_url="$1"
  local multiplier="$2"  # Cost multiplier for environment
  
  echo "Setting costs for environment: $env_url (multiplier: $multiplier)"
  
  # Base costs
  declare -A base_costs=(
    ["gpt-4"]="30.0:60.0"
    ["claude-3-sonnet"]="3.0:15.0"
    ["gpt-3.5-turbo"]="0.5:1.5"
  )
  
  for model in "${!base_costs[@]}"; do
    IFS=':' read -r input_cost output_cost <<< "${base_costs[$model]}"
    
    # Apply multiplier
    adjusted_input=$(echo "$input_cost * $multiplier" | bc -l)
    adjusted_output=$(echo "$output_cost * $multiplier" | bc -l)
    
    echo "  $model: input=$adjusted_input, output=$adjusted_output"
    tg-set-token-costs \
      --model "$model" \
      -i "$adjusted_input" \
      -o "$adjusted_output" \
      -u "$env_url"
  done
}

# Production environment (full cost)
set_environment_costs "http://prod:8088/" 1.0

# Development environment (reduced cost for budgeting)
set_environment_costs "http://dev:8088/" 0.1
```

### Cost Update Automation
```bash
# Automated cost updates from pricing file
update_costs_from_file() {
  local pricing_file="$1"
  
  if [ ! -f "$pricing_file" ]; then
    echo "Pricing file not found: $pricing_file"
    return 1
  fi
  
  echo "Updating costs from: $pricing_file"
  
  # Expected format: model_id,input_cost,output_cost
  while IFS=',' read -r model input_cost output_cost; do
    # Skip header line
    if [ "$model" = "model_id" ]; then
      continue
    fi
    
    echo "Updating $model: input=$input_cost, output=$output_cost"
    tg-set-token-costs --model "$model" -i "$input_cost" -o "$output_cost"
    
  done < "$pricing_file"
}

# Create example pricing file
cat > model_pricing.csv << EOF
model_id,input_cost,output_cost
gpt-4,30.0,60.0
gpt-3.5-turbo,0.5,1.5
claude-3-sonnet,3.0,15.0
claude-3-haiku,0.25,1.25
EOF

# Update costs from file
update_costs_from_file "model_pricing.csv"
```

### Bulk Cost Management
```bash
# Bulk cost updates with validation
bulk_cost_update() {
  local updates=(
    "gpt-4-turbo:10.0:30.0"
    "gpt-4:30.0:60.0"
    "claude-3-opus:15.0:75.0"
    "claude-3-sonnet:3.0:15.0"
    "gemini-pro:0.5:1.5"
  )
  
  echo "Bulk cost update starting..."
  
  for update in "${updates[@]}"; do
    IFS=':' read -r model input_cost output_cost <<< "$update"
    
    # Validate costs are numeric
    if ! [[ "$input_cost" =~ ^[0-9]+\.?[0-9]*$ ]] || ! [[ "$output_cost" =~ ^[0-9]+\.?[0-9]*$ ]]; then
      echo "Error: Invalid cost format for $model"
      continue
    fi
    
    echo "Setting costs for $model..."
    if tg-set-token-costs --model "$model" -i "$input_cost" -o "$output_cost"; then
      echo "✓ Updated $model"
    else
      echo "✗ Failed to update $model"
    fi
  done
  
  echo "Bulk update completed"
}

bulk_cost_update
```

## Advanced Usage

### Cost Tier Management
```bash
# Manage different cost tiers
set_cost_tier() {
  local tier="$1"
  
  case "$tier" in
    "premium")
      echo "Setting premium tier costs..."
      tg-set-token-costs --model "gpt-4" -i 30.0 -o 60.0
      tg-set-token-costs --model "claude-3-opus" -i 15.0 -o 75.0
      ;;
    "standard")
      echo "Setting standard tier costs..."
      tg-set-token-costs --model "gpt-3.5-turbo" -i 0.5 -o 1.5
      tg-set-token-costs --model "claude-3-sonnet" -i 3.0 -o 15.0
      ;;
    "budget")
      echo "Setting budget tier costs..."
      tg-set-token-costs --model "claude-3-haiku" -i 0.25 -o 1.25
      tg-set-token-costs --model "local-model" -i 0.0 -o 0.0
      ;;
    *)
      echo "Unknown tier: $tier"
      echo "Available tiers: premium, standard, budget"
      return 1
      ;;
  esac
}

# Set costs for different tiers
set_cost_tier "premium"
set_cost_tier "standard"
set_cost_tier "budget"
```

### Dynamic Pricing Updates
```bash
# Update costs based on current market rates
update_dynamic_pricing() {
  local pricing_api_url="$1"  # Hypothetical pricing API
  
  echo "Fetching current pricing from: $pricing_api_url"
  
  # This would integrate with actual pricing APIs
  # For demonstration, using static data
  
  declare -A current_prices=(
    ["gpt-4"]="30.0:60.0"
    ["gpt-3.5-turbo"]="0.5:1.5"
    ["claude-3-sonnet"]="3.0:15.0"
  )
  
  for model in "${!current_prices[@]}"; do
    IFS=':' read -r input_cost output_cost <<< "${current_prices[$model]}"
    
    echo "Updating $model with current market rates..."
    tg-set-token-costs --model "$model" -i "$input_cost" -o "$output_cost"
  done
}
```

### Cost Validation
```bash
# Validate cost settings
validate_costs() {
  local model="$1"
  local input_cost="$2"
  local output_cost="$3"
  
  echo "Validating costs for $model..."
  
  # Check cost reasonableness
  if (( $(echo "$input_cost < 0" | bc -l) )); then
    echo "Error: Input cost cannot be negative"
    return 1
  fi
  
  if (( $(echo "$output_cost < 0" | bc -l) )); then
    echo "Error: Output cost cannot be negative"
    return 1
  fi
  
  # Check if output cost is typically higher
  if (( $(echo "$output_cost < $input_cost" | bc -l) )); then
    echo "Warning: Output cost is lower than input cost (unusual but not invalid)"
  fi
  
  # Check for extremely high costs
  if (( $(echo "$input_cost > 100" | bc -l) )) || (( $(echo "$output_cost > 200" | bc -l) )); then
    echo "Warning: Costs are unusually high"
  fi
  
  echo "Validation passed for $model"
  return 0
}

# Validate before setting
if validate_costs "gpt-4" 30.0 60.0; then
  tg-set-token-costs --model "gpt-4" -i 30.0 -o 60.0
fi
```

## Error Handling

### Missing Required Arguments
```bash
Exception: error: the following arguments are required: --model, -i/--input-costs, -o/--output-costs
```
**Solution**: Provide all required arguments: model ID, input cost, and output cost.

### Invalid Cost Values
```bash
Exception: argument -i/--input-costs: invalid float value
```
**Solution**: Ensure cost values are valid numbers (e.g., 1.5, not "1.5a").

### API Connection Issues
```bash
Exception: Connection refused
```
**Solution**: Check API URL and ensure TrustGraph is running.

### Configuration Access Errors
```bash
Exception: Access denied to configuration
```
**Solution**: Verify user permissions for configuration management.

## Cost Monitoring Integration

### Cost Verification
```bash
# Verify costs were set correctly
verify_costs() {
  local model="$1"
  
  echo "Verifying costs for model: $model"
  
  # Check current settings
  if costs=$(tg-show-token-costs | grep "$model"); then
    echo "Current costs: $costs"
  else
    echo "Error: No costs found for model $model"
    return 1
  fi
}

# Set and verify
tg-set-token-costs --model "test-model" -i 1.0 -o 2.0
verify_costs "test-model"
```

### Cost Reporting Integration
```bash
# Generate cost report after updates
generate_cost_report() {
  local report_file="cost_report_$(date +%Y%m%d_%H%M%S).txt"
  
  echo "Cost Configuration Report - $(date)" > "$report_file"
  echo "======================================" >> "$report_file"
  
  tg-show-token-costs >> "$report_file"
  
  echo "Report generated: $report_file"
}

# Update costs and generate report
tg-set-token-costs --model "gpt-4" -i 30.0 -o 60.0
generate_cost_report
```

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-show-token-costs`](tg-show-token-costs.md) - Display current token costs
- [`tg-show-config`](tg-show-config.md) - Show configuration settings (if available)

## API Integration

This command uses the [Config API](../apis/api-config.md) to store token cost configuration in TrustGraph's configuration system.

## Best Practices

1. **Regular Updates**: Keep costs current with market rates
2. **Validation**: Validate cost values before setting
3. **Documentation**: Document cost sources and update procedures
4. **Environment Consistency**: Maintain consistent costs across environments
5. **Monitoring**: Track cost changes over time
6. **Backup**: Export cost configurations for backup
7. **Automation**: Automate cost updates where possible

## Troubleshooting

### Costs Not Taking Effect
```bash
# Verify costs were set
tg-show-token-costs | grep "model-name"

# Check API connectivity
curl -s "$TRUSTGRAPH_URL/api/v1/config" > /dev/null
```

### Incorrect Cost Calculations
```bash
# Verify cost format (per million tokens)
# $30 per million tokens = 30.0, not 0.00003

# Check decimal precision
echo "scale=6; 30/1000000" | bc -l  # This gives cost per token
```

### Permission Issues
```bash
# Check configuration access
tg-show-token-costs

# Verify user has admin privileges for cost management
```