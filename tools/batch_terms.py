"""batch_terms.py: rewrite work/tl/terms_*.txt from the current glossary, between translator waves. Agents only read them."""
import batches

rows = batches.glossary_rows()
for f in sorted(batches.TL.glob('b[0-9][0-9][0-9].tsv')):
    text = f.read_text(encoding='utf-8')
    terms = [line for jps, _, line in rows if any(j and j in text for j in jps)]
    (batches.TL / f'terms_{f.stem}.txt').write_text('\n'.join(terms) + '\n', encoding='utf-8', newline='\n')
