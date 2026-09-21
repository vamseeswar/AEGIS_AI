"""AEGIS AI — Smart Document-Aware Mock LLM Provider
A high-quality deterministic provider that performs actual document comprehension
by extracting and structuring the exact requested information from context documents.
Used as primary provider when Gemini API key is unavailable/expired.
"""

import asyncio
import re
from collections.abc import AsyncGenerator

from backend.ai.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Smart document-comprehension mock that reads context and returns precise answers."""

    def __init__(self, model_name: str = "mock-aegis-core", delay_per_token: float = 0.0):
        super().__init__(model_name=model_name)
        self.delay_per_token = delay_per_token

    def _extract_documents(self, combined_text: str) -> list[dict]:
        """Extracts all document blocks from the XML context."""
        doc_pattern = re.compile(
            r'<document\s+index="(\d+)"\s+token="([^"]+)"\s+title="([^"]+)"\s+page="(\d+)">(.*?)</document>',
            re.DOTALL
        )
        documents = []
        for match in doc_pattern.finditer(combined_text):
            documents.append({
                "index": match.group(1),
                "token": match.group(2),
                "title": match.group(3),
                "page": match.group(4),
                "content": match.group(5).strip(),
            })
        return documents

    def _extract_contact_info(self, content: str, token: str) -> str | None:
        """Extracts contact details from document text."""
        lines = []
        
        # Email detection
        emails = re.findall(r'[\w.\-+]+@[\w.\-]+\.\w+', content)
        for email in emails:
            lines.append(f"- **Email:** {email}")
        
        # Phone detection  
        phones = re.findall(r'(?:\+?\d[\d\s\-().]{7,15}\d)', content)
        for phone in phones:
            p = phone.strip()
            if len(re.sub(r'\D', '', p)) >= 7:
                lines.append(f"- **Phone:** {p}")
        
        # LinkedIn detection
        linkedin = re.findall(r'(?:linkedin\.com/in/[\w\-]+|LinkedIn)', content)
        if linkedin:
            lines.append(f"- **LinkedIn:** {linkedin[0]}")
        
        # GitHub detection
        github = re.findall(r'(?:github\.com/[\w\-]+|GitHub)', content)
        if github:
            lines.append(f"- **GitHub:** {github[0]}")
        
        # Location detection
        location = re.findall(r'(?:Bangalore|Mumbai|Delhi|Hyderabad|Chennai|Pune|India|[A-Z][a-z]+,\s*India)', content)
        if location:
            lines.append(f"- **Location:** {location[0]}")
        
        if lines:
            return f"Contact details from **{token}**:\n" + "\n".join(lines)
        return None

    def _extract_skills(self, content: str, token: str) -> str | None:
        """Extracts skills information from document text."""
        # Look for skills sections
        skill_patterns = [
            r'(?:Skills?|Technologies?|Technical\s+Skills?|Competencies)[:\s]*\n?(.*?)(?:\n\n|\Z)',
            r'Python[,\s]+(?:[\w\s,]+)',
        ]
        
        # Find technology keywords
        tech_keywords = re.findall(
            r'\b(?:Python|JavaScript|TypeScript|Java|C\+\+|SQL|FastAPI|React|Node\.js|'
            r'REST\s*APIs?|RAG|LLMs?|LangChain|LangGraph|Vector\s*Databases?|'
            r'Machine\s*Learning|Deep\s*Learning|GenAI|AI|NLP|Docker|AWS|'
            r'PostgreSQL|SQLite|MongoDB|Git|FastAPI|Django|Flask|'
            r'Pandas|NumPy|TensorFlow|PyTorch|Scikit[\-\s]learn|'
            r'Hugging\s*Face|OpenAI|Gemini|BERT|GPT)\b',
            content,
            re.IGNORECASE
        )
        
        unique_skills = list(dict.fromkeys(tech_keywords))  # Deduplicate preserving order
        
        if unique_skills:
            skill_list = ", ".join(unique_skills)
            return f"Skills found in **{token}**:\n{skill_list}"
        return None

    def _extract_experience(self, content: str, token: str) -> str | None:
        """Extracts work experience from document text."""
        # Find company/role patterns
        exp_pattern = re.compile(
            r'([A-Z][A-Za-z\s]+(?:AI|Tech|Systems?|Solutions?|Software|Services?|Pvt\.?\s*Ltd\.?|Inc\.?)?)'
            r'\s*[\n|]?\s*'
            r'([A-Za-z\s]+(?:Engineer|Developer|Analyst|Intern|Manager|Lead|Architect))'
            r'[^\n]*'
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}[^\n]*)',
            re.MULTILINE
        )
        
        experiences = []
        for m in exp_pattern.finditer(content):
            experiences.append(f"- **{m.group(2).strip()}** at {m.group(1).strip()} ({m.group(3).strip()})")
        
        if experiences:
            return f"Work experience in **{token}**:\n" + "\n".join(experiences[:5])
        return None

    def _synthesize_answer(self, messages: list[dict[str, str]]) -> str:
        combined_text = "\n".join(m.get("content", "") for m in messages)
        last_user_message = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_message = m.get("content", "").strip()
                break

        documents = self._extract_documents(combined_text)

        if not documents:
            return (
                f"No documents found in the knowledge base for your query: \"{last_user_message}\"\n\n"
                "Please upload documents via the **Documents** page to enable document-grounded answers.\n\n"
                "> ⚠️ **Note:** For full AI-powered responses, please add a valid Gemini API key to your `.env` file. "
                "Get a free key at [aistudio.google.com](https://aistudio.google.com)."
            )

        query_lower = last_user_message.lower()
        
        # Determine what the user is asking for
        is_contact_query = any(kw in query_lower for kw in [
            "contact", "email", "phone", "location", "address", "linkedin", "github", "reach"
        ])
        is_skills_query = any(kw in query_lower for kw in [
            "skill", "technolog", "stack", "expertise", "proficient", "know", "language", "framework", "tool"
        ])
        is_experience_query = any(kw in query_lower for kw in [
            "experience", "work", "job", "intern", "company", "role", "position", "employ"
        ])
        is_education_query = any(kw in query_lower for kw in [
            "education", "degree", "college", "university", "study", "graduate", "btech", "b.tech"
        ])
        is_project_query = any(kw in query_lower for kw in [
            "project", "built", "developed", "created", "system", "application", "portfolio"
        ])
        is_summary_query = any(kw in query_lower for kw in [
            "summary", "about", "overview", "profile", "who is", "describe", "tell me about"
        ])

        results = []
        all_content = " ".join(d["content"] for d in documents)
        all_tokens = " | ".join(d["token"] for d in documents)

        if is_contact_query:
            contact_found = False
            for doc in documents:
                contact = self._extract_contact_info(doc["content"], doc["token"])
                if contact:
                    results.append(contact)
                    contact_found = True
            
            if not contact_found:
                # Search for any email/phone in all content
                emails = re.findall(r'[\w.\-+]+@[\w.\-]+\.\w+', all_content)
                phones = re.findall(r'(?:\+91[\-\s]?\d{10}|\d{10})', all_content)
                if emails or phones:
                    r = f"Contact information found in documents ({all_tokens}):\n"
                    for e in set(emails):
                        r += f"- **Email:** {e}\n"
                    for p in set(phones):
                        r += f"- **Phone:** {p}\n"
                    results.append(r)
                else:
                    results.append(
                        f"No explicit contact details found in the retrieved document sections. "
                        f"The contact information may be on a different page or section. "
                        f"Try re-uploading the full document."
                    )

        elif is_skills_query:
            for doc in documents:
                skills = self._extract_skills(doc["content"], doc["token"])
                if skills:
                    results.append(skills)
            if not results:
                results.append(f"Skills section not found in the retrieved chunks from {all_tokens}. Try re-indexing the document.")

        elif is_experience_query:
            for doc in documents:
                exp = self._extract_experience(doc["content"], doc["token"])
                if exp:
                    results.append(exp)
            
            if not results:
                # Fallback: extract lines that look like job entries
                for doc in documents[:3]:
                    content_preview = doc["content"][:600]
                    results.append(f"From **{doc['title']}** {doc['token']}:\n{content_preview}")

        elif is_education_query:
            edu_matches = re.findall(
                r'(?:B\.?Tech|M\.?Tech|MBA|B\.?Sc|M\.?Sc|Bachelor|Master|Ph\.?D)[^\n.]*(?:\n[^\n]+)?',
                all_content, re.IGNORECASE
            )
            if edu_matches:
                results.append(f"Education from documents ({all_tokens}):\n" + "\n".join(f"- {e.strip()}" for e in edu_matches[:5]))
            else:
                results.append(f"No explicit education section found in retrieved chunks.")

        elif is_project_query:
            proj_matches = re.findall(
                r'(?:[A-Z][A-Za-z\s]+(?:System|Platform|App|Application|Solution|Tool|Pipeline|Assistant|Bot))[^\n]*(?:\n[^\n]{0,200})?',
                all_content
            )
            if proj_matches:
                results.append(f"Projects found ({all_tokens}):\n" + "\n".join(f"- {p.strip()[:150]}" for p in proj_matches[:5]))
            else:
                for doc in documents[:2]:
                    results.append(f"From **{doc['title']}** {doc['token']}:\n{doc['content'][:400]}")

        else:
            # General query: return the most relevant document sections
            for doc in documents[:3]:
                results.append(f"From **{doc['title']}** (page {doc['page']}) {doc['token']}:\n{doc['content'][:500]}")

        if results:
            answer = f"**Query:** {last_user_message}\n\n"
            answer += "\n\n---\n\n".join(results)
            answer += (
                "\n\n---\n"
                "> ⚠️ **Using AEGIS Core (Offline Engine).** For true AI-powered analysis, select "
                "**Gemini 1.5 Flash ⚡** in the Active Intelligence Engine dropdown. "
                "You'll need a valid Gemini API key in your `.env` file — get one free at "
                "[aistudio.google.com](https://aistudio.google.com)."
            )
            return answer

        # Final fallback
        return (
            f"I searched the knowledge base for: \"{last_user_message}\"\n\n"
            f"Retrieved {len(documents)} document chunk(s) but couldn't extract specific structured information for this query.\n\n"
            f"Raw document preview:\n{documents[0]['content'][:400] if documents else 'No content'}\n\n"
            "> ⚠️ **Using AEGIS Core (Offline Engine).** For full AI answers, use Gemini 1.5 Flash ⚡."
        )

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        return self._synthesize_answer(messages)

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        full_text = self._synthesize_answer(messages)
        words = re.findall(r"\S+|\s+", full_text)

        for word in words:
            if self.delay_per_token > 0:
                await asyncio.sleep(self.delay_per_token)
            yield word
