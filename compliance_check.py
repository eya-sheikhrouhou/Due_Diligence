import dash
from dash import html, dcc, Input, Output, State, no_update
import base64
import fitz  # PyMuPDF
import tempfile
import re
import io
from transformers import pipeline

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

# Initialize the model (lazy load)
compliance_model = None

# Compliance rules with patterns and regulations
COMPLIANCE_RULES = [
    # ========= HIGH RISK (FRAUD/AML) =========
    {
        "pattern": r"\(No\s+KYC\)|investments?\s+under\s+\$?1M?\b",
        "regulation": "FATF Recommendation 10 + FinCEN $3K Rule",
        "risk": "Critical",
        "recommendation": "Implement KYC for ALL transactions regardless of amount"
    },
    {
        "pattern": r"simplified\s+onboarding|express\s+verification",
        "regulation": "5AMLD Article 13",
        "risk": "High",
        "recommendation": "Require full identity documents for all customers"
    },

    # ===== OFFSHORE ACCOUNT ENHANCEMENTS =====
    {
        "pattern": r"Cayman\s+Islands.*no\s+tax\s+reporting",
        "regulation": "CRS (Common Reporting Standard)",
        "risk": "Critical",
        "recommendation": "Register for automatic tax information exchange"
    },
    {
        "pattern": r"shielded\s+banking\s+relationships",
        "regulation": "EU Tax Haven Blacklist",
        "risk": "High",
        "recommendation": "Disclose all banking partners to regulators"
    },

    # ===== AUDIT & FINANCIAL CONTROLS =====
    {
        "pattern": r"no\s+audit\s+since\s+\d{4}",
        "regulation": "PCAOB AS 3101",
        "risk": "High",
        "recommendation": "Conduct back-audits for missing years + current audit"
    },
    {
        "pattern": r"internal\s+controls\s+only",
        "regulation": "SOX 404",
        "risk": "Medium",
        "recommendation": "Implement external control testing framework"
    },

    # ===== GDPR/PRIVACY ENHANCEMENTS =====
    {
        "pattern": r"reserve\s+the\s+right\s+to\s+sell\s+data",
        "regulation": "GDPR Article 7/CCPA 1798.120",
        "risk": "Critical",
        "recommendation": "Rewrite privacy policy to require explicit opt-in consent"
    },
    {
        "pattern": r"gdpr\s+not\s+applicable",
        "regulation": "GDPR Article 3 (Extra-Territoriality)",
        "risk": "High",
        "recommendation": "Appoint EU representative if processing any EU data"
    },

    # ===== SEC REGISTRATION ENHANCEMENTS =====
    {
        "pattern": r"not\s+registered\s+with\s+SEC.*no\s+plans\s+to\s+register",
        "regulation": "Securities Act Section 5 + Rule 506(c)",
        "risk": "Critical",
        "recommendation": "Immediately file Form D or cease offerings"
    },

    # ===== GUARANTEED RETURNS ENHANCEMENTS =====
    {
        "pattern": r"25%\s+monthly.*no\s+risk",
        "regulation": "SEC Rule 10b-5 + FINRA 2210",
        "risk": "Critical",
        "recommendation": """
            1. Remove all return claims
            2. Add: "Hypothetical returns, risk of total loss"
            3. SEC pre-approve all marketing materials"""
    },

    # ===== COOLING-OFF PERIOD RULES =====
    {
        "pattern": r"no\s+cooling\-off.*binding\s+commitment",
        "regulation": "FTC Rule 16 CFR §429.1",
        "risk": "Medium",
        "recommendation": "Implement 14-day cancellation right for all contracts"
    },

    # ===== NEW: WHISTLEBLOWER PROTECTIONS =====
    {
        "pattern": r"confidentiality\s+agreement.*report",
        "regulation": "Dodd-Frank §922",
        "risk": "High",
        "recommendation": "Add whistleblower carve-out to all NDAs"
    },

    # ===== NEW: CRYPTO-SPECIFIC RISKS =====
    {
        "pattern": r"non\-custodial\s+wallets.*no\s+tracking",
        "regulation": "FATF Travel Rule (2021)",
        "risk": "High",
        "recommendation": "Implement VASP protocols for all crypto transfers"
    },
    {
        "pattern": r"defi\s+platform.*no\s+kyc",
        "regulation": "FinCEN 2019 Guidance",
        "risk": "Critical",
        "recommendation": "Register as MSB and implement chainalysis"
    },

    # ===== NEW: SANCTIONS SCREENING =====
    {
        "pattern": r"global\s+clients.*no\s+screening",
        "regulation": "OFAC 50% Rule",
        "risk": "Critical",
        "recommendation": "Implement real-time sanctions screening (e.g., Refinitiv)"
    },
    {
        "pattern": r"\b(no\s+(id|kyc|paperwork|documents?)|without\s+verification)\b",
        "regulation": "AML/KYC Requirements",
        "risk": "High",
        "recommendation": "Implement full identity verification for all investors"
    },
    {
        "pattern": r"\b(anonymous|numbered)\s+(accounts?|wallets?)\b",
        "regulation": "FATF Recommendation 10",
        "risk": "Critical",
        "recommendation": "Disclose all beneficial ownership information"
    },
    
    # ========= TAX EVASION =========
    {
        "pattern": r"\b(offshore|tax\s+haven|cayman|bvi|panama)\b.*?\b(account|fund|entity)\b",
        "regulation": "IRS Foreign Account Compliance",
        "risk": "High",
        "recommendation": "File FBAR and FATCA disclosures"
    },
    {
        "pattern": r"\b(untraceable|unreported)\s+(income|assets)\b",
        "regulation": "IRC §7201 (Tax Evasion)",
        "risk": "Critical",
        "recommendation": "Amend tax filings with proper disclosures"
    },
    
    # ========= SECURITIES VIOLATIONS =========
    {
        "pattern": r"\b(unregistered)\s+(security|offering)\b",
        "regulation": "Securities Act §5",
        "risk": "High",
        "recommendation": "File Form D or register with SEC"
    },
    {
        "pattern": r"\b(secret|proprietary)\s+(algorithm|strategy|formula)\b",
        "regulation": "SEC Marketing Rule",
        "risk": "Medium",
        "recommendation": "Disclose all material facts and risks"
    },
    
    # ========= CRYPTO RISKS =========
    {
        "pattern": r"\b(unlicensed)\s+(crypto|digital\s+asset)\s+(exchange|platform)\b",
        "regulation": "FinCEN MSB Requirements",
        "risk": "High",
        "recommendation": "Register as Money Services Business"
    },
    {
        "pattern": r"\b(mixing|tumbling)\s+services?\b",
        "regulation": "Anti-Money Laundering Act",
        "risk": "Critical",
        "recommendation": "Cease operations and file SAR"
    },
    
    # ========= INVESTOR PROTECTION =========
    
    {
        "pattern": r"\b(instant|immediate)\s+(returns|profits)\b",
        "regulation": "CFTC Anti-Fraud Provisions",
        "risk": "High",
        "recommendation": "Remove unrealistic timeframes"
    },
    
    # ========= SANCTIONS RISKS =========
    {
        "pattern": r"\b(russia|iran|north korea)\s+(investments?|clients?)\b",
        "regulation": "OFAC Sanctions",
        "risk": "Critical",
        "recommendation": "Block transactions and file report"
    },
    
    # ========= PRIVACY VIOLATIONS =========
    {
        "pattern": r"\b(share|sell)\s+client\s+data\b",
        "regulation": "GDPR/CCPA",
        "risk": "High",
        "recommendation": "Implement data protection measures"
    },
    
    # ========= OPERATIONAL RISKS =========
    {
        "pattern": r"\b(no\s+audit|unaudited)\b",
        "regulation": "AICPA Standards",
        "risk": "Medium",
        "recommendation": "Conduct annual third-party audits"
    },
    {
        "pattern": r"\b(manual\s+processes|spreadsheets?)\s+for\s+accounting\b",
        "regulation": "SOX Compliance",
        "risk": "Medium",
        "recommendation": "Implement proper accounting systems"
    },
    {
        "pattern": r"no\s+(paperwork|documentation|id|kyc)\s+required",
        "regulation": "AML/KYC Regulations",
        "risk": "High",
        "recommendation": "Implement full KYC procedures for all investors"
    },
    {
        "pattern": r"anonymous\s+(numbered\s+)?accounts?",
        "regulation": "Tax Evasion Risk",
        "risk": "Critical",
        "recommendation": "Disclose all account information to regulators"
    },
    {
        "pattern": r"untraceable\s+cryptocurrency",
        "regulation": "FinCEN Travel Rule",
        "risk": "High",
        "recommendation": "Implement cryptocurrency transaction monitoring"
    },
    {
        "pattern": r"operate\s+outside\s+financial\s+authorities",
        "regulation": "Regulatory Circumvention",
        "risk": "Critical",
        "recommendation": "Register with appropriate financial regulators"
    },
    {
    "pattern": r"\b(swift|wire)\s+transfers?\s+without\s+questions\b",
    "regulation": "FATF Recommendation 16",
    "risk": "High",
    "recommendation": "Implement wire transfer due diligence"
    },
    {
    "pattern": r"\b(limited\s+time|act\s+now)\b.*?\b(offer|discount)\b",
    "regulation": "FTC Cooling-Off Rule",
    "risk": "Medium",
    "recommendation": "Remove high-pressure sales tactics"
    },
    {
    "pattern": r"\b(ai\-generated|chatgpt)\s+investment\s+advice\b",
    "regulation": "SEC Reg BI",
    "risk": "Medium",
    "recommendation": "Disclose AI usage and limitations"
    },
    {
    "pattern": r"\b(privacy\s+coin|monero|zcash)\b",
    "regulation": "Travel Rule Compliance",
    "risk": "High",
    "recommendation": "Implement blockchain analytics tools"
    }
]

# Add these to your existing COMPLIANCE_RULES list






# Style for the upload component
upload_style = {
    'width': '80%',
    'height': '60px',
    'lineHeight': '60px',
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '5px',
    'textAlign': 'center',
    'margin': '20px auto',
    'cursor': 'pointer'
}

def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF bytes"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc[:3]:  # Only first 3 pages
        text += page.get_text()
        if len(text) > 2000:  # Limit text
            break
    return text[:2000]

def analyze_text(text):
    """Analyze text for compliance issues"""
    global compliance_model
    
    issues = []
    for rule in COMPLIANCE_RULES:
        matches = re.finditer(rule["pattern"], text, re.IGNORECASE)
        for match in matches:
            issues.append({
                "text": match.group(),
                "regulation": rule["regulation"],
                "risk": rule["risk"],
                "recommendation": rule["recommendation"],
                "start": match.start(),
                "end": match.end()
            })
    
    # Calculate score (10 - number of issues, minimum 1)
    score = max(1, 10 - len(issues))
    
    # Get unique recommendations
    recommendations = list({issue["recommendation"] for issue in issues})
    
    return {
        "issues": issues,
        "score": f"{score}/10",
        "recommendations": recommendations if recommendations else ["No specific recommendations needed"]
    }

def highlight_pdf(pdf_bytes, issues):
    """Add red highlights to issues in PDF"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        for issue in issues:
            text_instances = page.search_for(issue["text"])
            for inst in text_instances:
                highlight = page.add_highlight_annot(inst)
                highlight.set_colors({"stroke": (1, 0, 0)})  # Red color
                highlight.update()
    return doc.tobytes()

# App layout
app.layout = html.Div([
    html.Div([
        html.H1("Compliance Analyzer PRO", style={'textAlign': 'center'}),
        html.P("Upload investment documents to check for regulatory compliance issues", 
              style={'textAlign': 'center'})
    ], style={'marginBottom': '30px'}),
    
    dcc.Upload(
        id='upload-pdf',
        children=html.Div([
            html.I(className="fas fa-file-upload", style={'marginRight': '10px'}),
            'Drag & Drop or Select PDF'
        ]),
        style=upload_style,
        multiple=False
    ),
    
    dcc.Loading(
        id="loading",
        type="circle",
        children=[
            html.Div(id='pdf-viewer-container', style={'margin': '20px auto', 'width': '80%'}),
            html.Div(id='analysis-results', style={
                'width': '80%',
                'margin': '20px auto',
                'padding': '20px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 10px rgba(0,0,0,0.1)'
            })
        ]
    )
])

@app.callback(
    [Output('pdf-viewer-container', 'children'),
     Output('analysis-results', 'children')],
    Input('upload-pdf', 'contents'),
    prevent_initial_call=True
)
def update_output(contents):
    if not contents:
        return no_update, no_update
    
    try:
        # Process uploaded file
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Analyze text
        text = extract_text_from_pdf(io.BytesIO(decoded))
        analysis = analyze_text(text)
        
        # Highlight PDF
        highlighted_pdf = highlight_pdf(decoded, analysis["issues"])
        pdf_url = f"data:application/pdf;base64,{base64.b64encode(highlighted_pdf).decode()}"
        
        # Create viewer
        viewer = html.Iframe(
            src=pdf_url,
            style={
                'width': '100%',
                'height': '500px',
                'border': '1px solid #ddd'
            }
        )
        
        # Create results display
        results = html.Div([
            html.H2("Compliance Analysis Report", style={'textAlign': 'center'}),
            
            html.Div([
                html.Div([
                    html.H3("Compliance Status"),
                    html.Div(
                        analysis["score"],
                        style={
                            'fontSize': '24px',
                            'fontWeight': 'bold',
                            'color': '#4CAF50' if int(analysis["score"][0]) > 5 else '#F44336',
                            'textAlign': 'center',
                            'margin': '10px 0'
                        }
                    )
                ], style={
                    'padding': '15px',
                    'backgroundColor': '#f8f9fa',
                    'borderRadius': '8px',
                    'marginBottom': '20px'
                }),
                
                html.Div([
                    html.H3("Identified Issues"),
                    html.Ul([
                        html.Li(
                            [
                                html.Span(f'"{issue["text"]}" → ', style={'color': '#F44336'}),
                                html.Span(issue["regulation"]),
                                html.Span(f' (Risk: {issue["risk"]})')
                            ],
                            style={'marginBottom': '8px'}
                        ) 
                        for issue in analysis["issues"]
                    ], style={'paddingLeft': '20px'})
                ], style={
                    'padding': '15px',
                    'backgroundColor': '#ffeeee',
                    'borderLeft': '4px solid #F44336',
                    'borderRadius': '8px',
                    'marginBottom': '20px'
                }),
                
                html.Div([
                    html.H3("Recommendations"),
                    html.Ul([
                        html.Li(rec, style={'marginBottom': '8px'}) 
                        for rec in analysis["recommendations"]
                    ], style={'paddingLeft': '20px'})
                ], style={
                    'padding': '15px',
                    'backgroundColor': '#f0fff4',
                    'borderLeft': '4px solid #4CAF50',
                    'borderRadius': '8px'
                })
            ])
        ])
        
        return viewer, results
    
    except Exception as e:
        error_message = html.Div([
            html.H3("Analysis Error", style={'color': '#F44336'}),
            html.P(str(e)),
            html.P("Please try again with a different PDF file.")
        ], style={
            'padding': '20px',
            'backgroundColor': '#ffebee',
            'borderRadius': '8px',
            'textAlign': 'center'
        })
        return no_update, error_message

if __name__ == '__main__':
    app.run(debug=True)