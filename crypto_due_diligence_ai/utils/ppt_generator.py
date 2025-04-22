from pptx import Presentation
from pptx.util import Inches
import io

def generate_ppt(question, answer, red_flag):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Due Diligence Summary"
    flag_text = "⚠️ RED FLAG DETECTED" if red_flag else "✅ No Red Flags"
    content.text = f"Question: {question}\n\nAnswer: {answer}\n\n{flag_text}"

    ppt_io = io.BytesIO()
    prs.save(ppt_io)
    ppt_io.seek(0)
    return ppt_io