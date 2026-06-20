import re

class NLIVerifier:
    def verify_entailment(self, claim: str, source: str) -> bool:
        # Clean citation markers like [S1], [S2]
        claim_clean = re.sub(r"\[S\d+\]", "", claim)
        source_clean = re.sub(r"\[S\d+\]", "", source)

        # Lowercase comparisons
        claim_lower = claim_clean.lower()
        source_lower = source_clean.lower()
        
        # Extract potential capitalized entities in Vietnamese from the claim
        words = claim_clean.split()
        entities = []
        current_entity = []
        for i, w in enumerate(words):
            # Clean punctuation
            w_clean = re.sub(r"[^\w\s]", "", w)
            if not w_clean:
                continue
            # If it is capitalized (first character is upper, rest not necessarily)
            if w_clean[0].isupper() and not w_clean.isdigit():
                current_entity.append(w_clean)
            else:
                if current_entity:
                    entities.append(" ".join(current_entity))
                    current_entity = []
        if current_entity:
            entities.append(" ".join(current_entity))
            
        # Clean entities
        cleaned_entities = []
        for ent in entities:
            ent_lower = ent.lower()
            if ent_lower in ["không", "nhưng", "tuy", "vì", "tại", "trong", "theo", "dưới"]:
                continue
            if len(ent) > 1:
                cleaned_entities.append(ent)
                
        # If any extracted entity is NOT in the source text (case-insensitive), claim is unsupported
        for ent in cleaned_entities:
            ent_clean = ent.lower().strip()
            # If the entity is the first word of the claim, check if it contains multiple capitalized words
            first_word = claim.strip().split()[0] if claim.strip() else ""
            first_word_clean = re.sub(r"[^\w\s]", "", first_word)
            if ent == first_word_clean and len(ent.split()) == 1:
                continue
            
            if ent_clean not in source_lower:
                return False
                
        return True
