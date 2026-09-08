# Demo narration (≈2:45 at a natural pace)

Replace [YOUR NAME] before generating audio. Digit-by-digit postal codes and
em-dashes are intentional — they make AI text-to-speech read more naturally.

---

Hi, my name is [YOUR NAME], and this is my submission for the Superjoin engineering intern assignment: a Fact Knowledge Layer.

The idea is simple. Important facts are scattered across documents, written in different ways — sometimes backed up by other sources, sometimes contradicted. This system reads PDFs, pulls out checkable facts, ties every fact back to the exact sentence it came from, and then works out how facts across documents relate: whether they corroborate each other, contradict each other, or can be reconciled once you account for context like time period, scope, or units.

It currently has six real documents loaded — three from the logistics company Delhivery, and three about the Indian economy from different institutions. That's over four hundred facts and around a hundred and fifty relationships. Nothing in the code is specific to these documents; the documents themselves decide what counts as a fact.

Let me walk through the four required cases.

First, a corroboration. In separate reports, the Reserve Bank of India and the International Monetary Fund both state that headline inflation for fiscal year 2024 to 25 was four point six percent. Same number, same period, two independent sources. The system labels this "corroborates", and quotes both sentences as the evidence.

Second, a genuine contradiction. Delhivery's corporate address appears in a 2022 prospectus and again in the 2024 annual report. Both say Plot 5, Sector 44, Gurugram — but one gives the postal code as one, two, two, zero, zero, two, and the other as one, two, two, zero, zero, one. Both quotes are word for word from their source pages, so this isn't an extraction error. It's a real one-digit inconsistency between two official filings — the kind of thing a person reading either document alone would never catch.

Third, an apparent contradiction that context explains. One report gives India's private consumption growth as seven point two percent for fiscal 2024 to 25. Another gives seven point five percent for 2022 to 23. The values differ, but the system recognises that these are different time periods, and marks it "reconcilable by context" rather than a conflict.

Fourth, a reasoning failure I found, and did not hide. The system compared the IMF's "2025 Q2" with India's fiscal "Q2 FY25" and treated them as the same quarter. They're actually about nine months apart. The underlying facts probably aren't in conflict — the mistake is in the comparison step, which trusted the surface similarity of the two labels. It's still there in the results, and in the write-up I explain the fix: normalise calendar quarters versus fiscal quarters during extraction, instead of trusting whatever label the document used.

Every fact you see here is grounded in a quote you can check, and the schema grows on its own as new kinds of documents come in. Thanks for watching.
