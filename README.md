# Fluency AI Research Agent

Multi-agent system for automated enterprise deployment research. Generates comprehensive intelligence briefs to support sales, security reviews, and deal strategy.

## Features

- **15+ Specialized Research Agents** - Each focused on a specific intelligence domain
- **LinkedIn Intelligence** - Executive profiles, thought leadership topics, strategic initiatives
- **Checkpoint/Resume** - Long-running pipelines can be resumed after interruption
- **Multiple Output Formats** - Markdown briefs + PDF reports with executive summaries
- **Rate Limit Handling** - Automatic retry with exponential backoff
- **Source Citations** - Every claim linked to evidence with quality indicators
- **Structured Logging** - Comprehensive logging for debugging and auditing
- **Configuration Management** - Environment-based configuration with sensible defaults

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd fluency-research-agent

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

Required: Python 3.10+, Anthropic API key

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | - | **Required** - Your Anthropic API key |
| `MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `OUTPUT_DIR` | `results` | Directory for output files |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MAX_RETRIES` | `5` | Maximum API retry attempts |
| `INITIAL_BACKOFF` | `30` | Initial retry backoff in seconds |
| `AGENT_DELAY` | `30` | Delay between agents in seconds |

## Usage

```bash
# Basic research (API key from environment)
python main.py stripe.com

# With explicit API key
python main.py stripe.com --api-key sk-ant-...

# Custom output directory
python main.py stripe.com --output ./my-research

# Resume interrupted pipeline
python main.py stripe.com --resume

# Quiet mode (less output)
python main.py stripe.com --quiet

# Show deployment score summary
python main.py stripe.com --show-score
```

## Research Agents

| Agent | Purpose | Key Outputs |
|-------|---------|-------------|
| **Discovery** | Company identification | Name, type, industry, size |
| **Security** | Compliance & certifications | SOC 2, ISO 27001, trust center |
| **Tech Stack** | Infrastructure & tools | Cloud provider, SSO, integrations |
| **Strategic** | News & initiatives | AI projects, partnerships, M&A |
| **Financials** | SEC filings (public cos) | Revenue, risk factors, CIK |
| **Job Postings** | Hiring signals | Real tech stack, growth areas |
| **Customer Reviews** | Sentiment analysis | Pain points, competitor mentions |
| **Regulatory Risk** | Compliance exposure | Breaches, enforcement, litigation |
| **Stakeholders** | Decision makers | Champions, org structure |
| **LinkedIn Intel** | Executive presence | Thought leadership, initiatives |
| **Operational Culture** | Methodology signals | SRE/Agile/ITSM patterns |
| **Shadow IT** | Legacy systems | Tech debt, hidden dependencies |
| **Local Regulations** | Regional compliance | GDPR, data localization |
| **Procurement** | Buying process | Budget cycles, approval timelines |
| **Implementation Risk** | Deployment risk | Change management, complexity |

## Output Files

Results are saved to `results/<domain>/`:

| File | Description |
|------|-------------|
| `executive_brief.md` | Deal intelligence with actionable insights |
| `sales_brief.md` | Sales positioning and talking points |
| `security_brief.md` | Compliance and security details |
| `product_brief.md` | Technical fit assessment |
| `*.pdf` | PDF versions with executive summary |
| `evidence.json` | Structured evidence graph |
| `raw_research.json` | Full agent outputs |
| `checkpoint.json` | Resume state (for `--resume`) |

## Example Output

The executive brief includes:

- **Quick Assessment** - Overall score, champion score, regulatory risk
- **Key Intelligence** - Hidden champions, budget signals, tech stack
- **Strategic Insights** - Cross-referenced findings with actions
- **Deal Intelligence** - Decision makers, budget indicators
- **Risk & Red Flags** - Blockers, concerns, competitive landscape
- **Relationship Mapping** - Technical leadership, LinkedIn profiles
- **Discovery Questions** - Tailored questions for first call

## Architecture

```
fluency-research-agent/
├── main.py                 # CLI entry point
├── pipeline.py             # Orchestrates the 4-stage pipeline
├── models.py               # Pydantic models for all data structures
├── config.py               # Configuration management
├── logger.py               # Logging framework
├── agents/
│   ├── base.py             # BaseAgent with tool use loop
│   ├── discovery.py        # Company identification
│   ├── security.py         # Security/compliance research
│   ├── tech_stack.py       # Technology detection
│   ├── strategic.py        # News and initiatives
│   ├── financials.py       # SEC EDGAR integration
│   ├── synthesis.py        # Combines all findings
│   └── ...                 # Additional specialized agents
├── generators/
│   ├── base.py             # Base generator classes
│   ├── executive_brief.py  # Main intelligence brief
│   ├── sales_brief.py      # Sales-focused output
│   ├── security_brief.py   # Security-focused output
│   ├── product_brief.py    # Product/technical output
│   └── pdf_generator.py    # PDF rendering
└── tools/
    ├── base.py             # Base tool classes
    ├── tool_definitions.py # web_fetch, crt.sh tools
    └── sec_edgar.py        # SEC filing retrieval
```

## Rate Limits

The pipeline handles Anthropic API rate limits automatically:

- **Configurable delay** between agents (default: 30 seconds)
- **Exponential backoff** with configurable retries (default: 5 attempts)
- **Checkpoint saves** after each agent completes

If you hit rate limits, wait a minute and run with `--resume`.

## Error Handling

The system includes comprehensive error handling:

- **Specific exception types** - Different handling for HTTP errors, timeouts, validation errors
- **Structured logging** - All errors logged with context for debugging
- **Graceful degradation** - Agents that fail are logged but don't crash the pipeline
- **Input validation** - URLs and other inputs validated before processing

## Development

### Adding New Agents

1. Create a new file in `agents/` inheriting from `BaseAgent`
2. Implement `name`, `system_prompt`, `tools`, and research method
3. Register in `agents/__init__.py`
4. Add to pipeline in `pipeline.py`

### Adding New Tools

1. Create tool class inheriting from `BaseTool` in `tools/`
2. Implement `name`, `description`, `input_schema`, and `execute` method
3. Register with tool registry or add to `TOOL_HANDLERS`

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html
```

## Security Best Practices

- **Never commit API keys** - Use environment variables or `.env` file
- **Results may contain sensitive data** - Handle output files appropriately
- **Rate limiting is enforced** - Respect Anthropic API limits
- **Validate all inputs** - URLs are validated before fetching

## Troubleshooting

### Rate Limit Errors

If you see rate limit errors:
1. Wait for the displayed backoff time
2. Run again with `--resume` to continue from last checkpoint

### API Key Issues

If API key errors occur:
1. Verify `ANTHROPIC_API_KEY` is set in `.env` or environment
2. Check the key is valid at console.anthropic.com

### Missing Dependencies

If `BeautifulSoup` or other packages are missing:
```bash
pip install -r requirements.txt
```

## License

MIT
