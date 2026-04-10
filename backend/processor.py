import json

class BureaucraticBrain:
    """
    [V3.1] PSST Master Brain
    Logic: Industry Analysis -> Quantitative Estimation -> Bureaucratic Drafting
    """
    
    def __init__(self):
        self.govt_blue = "#003366"

    def analyze_industry_context(self, industry):
        """
        [TAM-SAM-SOM & Metrics Mapping]
        Maps standard values for specific industries to provide realistic data.
        """
        # Industry-specific benchmark data
        benchmarks = {
            "반도체": {
                "tam": "1,200조", "sam": "45조", "som": "8,000억",
                "cac": "250만 원(B2B)", "ltv": "5억 원", "growth": "15.4%"
            },
            "SaaS": {
                "tam": "300조", "sam": "10조", "som": "500억",
                "cac": "5,000원(B2C)", "ltv": "15만 원", "growth": "25%"
            }
        }
        return benchmarks.get(industry, benchmarks["SaaS"]) # Default to SaaS logic

    def generate_psst_report(self, company_info):
        ctx = self.analyze_industry_context(company_info['industry'])
        
        report = {
            "problem": {
                "title": f"□ [{company_info['industry']}] 시장의 고비용·저효율 병목 현상",
                "evidence": f"○ 기존 방식 대비 <font color='{self.govt_blue}'><b>연간 {ctx['growth']}의 기회비용 손실</b></font> 발생 (출처: 관련 산업 백서)",
                "market": f"- 시장 규모(SAM): {ctx['sam']} 규모의 급성장하는 시장 타겟팅"
            },
            "solution": {
                "title": f"□ {company_info['core_tech']} 기반 수익 정당성 확보",
                "metrics": f"○ <b>Unit Economics</b>: 목표 CAC {ctx['cac']} 대비 LTV {ctx['ltv']}로 <font color='{self.govt_blue}'><b>수익성 극대화</b></font>"
            }
        }
        return report

if __name__ == "__main__":
    brain = BureaucraticBrain()
    company = {"name": "GrantAI", "industry": "반도체", "core_tech": "NPU 설계"}
    final_report = brain.generate_psst_report(company)
    print(json.dumps(final_report, indent=4, ensure_ascii=False))
