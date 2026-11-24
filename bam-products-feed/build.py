#!/usr/bin/env python3
"""Build the BAM products page and product feed files from one product list.

    pip install pyarrow
    python3 build.py

Edit PRODUCTS / the constants below, re-run, and re-upload the outputs.
"""
import csv
import gzip
import html
import json
from pathlib import Path

# --- Settings -----------------------------------------------------------------
SITE = "https://baminjurylaw.com"
PAGE_URL = f"{SITE}/products/"          # where the products page will live
CONTACT_URL = f"{SITE}/contact/"        # existing consultation form
PHONE_DISPLAY = "(801) 970-9913"
PHONE_TEL = "+18019709913"
FIRM = "BAM Personal Injury Lawyers"
# Gravity Forms shortcode for the existing consultation form (form ID 1 on /contact/).
FORM_SHORTCODE = '[gravityform id="1" title="false" description="false" ajax="true"]'
UPLOADS = f"{SITE}/wp-content/uploads"

IMG_CASE_EVAL = f"{UPLOADS}/2026/07/teamwork-process-young-business-managers-crew-working-with-new-startup-project-labtop-office-wood-table-typing-keyboard-texting-message-analyze-graph-plans-scaled.jpg"
IMG_CONSULT = f"{UPLOADS}/2026/11/interactive.jpg"
IMG_LETTER = f"{UPLOADS}/2026/06/pexels-pavel-danilyuk-8112199-scaled.jpg"
IMG_FOUNDERS = f"{UPLOADS}/2025/04/Contact-a-Personal-Injury-Lawyer-for-a-Free-Case-Consultation.jpg"
IMG_OFFICE = f"{UPLOADS}/2026/11/9b2fed7d-04eb-406d-96ba-6384f66da911-1536x1152.jpg"
LOGO = f"{UPLOADS}/2023/12/LOGO.svg"

PRODUCTS = [
    {
        "item_id": "bam-case-evaluation",
        "slug": "case-evaluation",
        "title": "Personal Injury Case Evaluation",
        "tagline": "Find out where your claim stands.",
        "description": (
            "A no-cost review of your injury claim by BAM Personal Injury Lawyers. "
            "Tell us what happened and our team looks at fault, insurance coverage, "
            "your medical treatment, and the deadlines that apply, then tells you "
            "plainly whether you have a case and what the next step is. Available "
            "for car, truck, motorcycle, pedestrian, and bicycle accidents, slip "
            "and falls, dog bites, and wrongful death claims in Utah and Idaho. "
            "No cost and no obligation. Submit your contact information online or "
            "call (801) 970-9913."
        ),
        "bullets": [
            "Review of fault, insurance coverage, and your injuries",
            "A straight answer on whether you have a claim",
            "The deadlines that apply to your case",
        ],
        "image": IMG_CASE_EVAL,
        "image_alt": "Attorney reviewing case documents with a client",
        "extra_images": [IMG_FOUNDERS],
    },
    {
        "item_id": "bam-free-consultation",
        "slug": "free-consultation",
        "title": "Free Consultation with a Personal Injury Lawyer",
        "tagline": "Talk it through with our team. No cost, no pressure.",
        "description": (
            "A free, confidential consultation with BAM Personal Injury Lawyers, "
            "by phone, video, or in person at our Murray, St. George, or Meridian "
            "office. Ask your questions, learn how the claims process works, and "
            "hear how we would approach your case. If we represent you, there is "
            "no fee unless we win. Serving injured people across Utah and Idaho. "
            "Request a consultation online or call (801) 970-9913."
        ),
        "bullets": [
            "Free and confidential",
            "By phone, video, or at one of our three offices",
            "No fee unless we win",
        ],
        "image": IMG_CONSULT,
        "image_alt": "BAM attorney meeting with a client in a conference room",
        "extra_images": [IMG_OFFICE, IMG_FOUNDERS],
    },
    {
        "item_id": "bam-insurance-letter",
        "slug": "strongly-worded-letter",
        "title": "Strongly-Worded Letter to the Insurance Co.",
        "tagline": "Put the insurance company on notice, in writing.",
        "description": (
            "Is the insurance company stalling, lowballing, or ignoring you? Start "
            "with a free review of your claim. If we take your case, an attorney "
            "at BAM Personal Injury Lawyers sends the insurer a formal letter on "
            "firm letterhead: it tells the adjuster you are represented, directs "
            "all communication to our office, demands that evidence be preserved, "
            "and lays out your claim. No upfront cost, and no fee unless we recover "
            "money for you. For injury claims in Utah and Idaho. Every case is "
            "different and past results do not guarantee an outcome. Submit your "
            "contact information online or call (801) 970-9913."
        ),
        "bullets": [
            "Tells the adjuster to deal with your lawyer, not you",
            "Demands that evidence be preserved",
            "No upfront cost; no fee unless we recover",
        ],
        "image": IMG_LETTER,
        "image_alt": "Lady Justice statue holding scales in a law office",
        "extra_images": [IMG_FOUNDERS],
    },
]

HERE = Path(__file__).parent
FEED_DIR = HERE / "feed"


def product_url(p):
    # Each product links to the existing contact form. The query string keeps
    # the URLs distinct per product and is ignored by the server.
    return f"{CONTACT_URL}?service={p['slug']}"


# --- Feed ---------------------------------------------------------------------
def feed_rows():
    rows = []
    for p in PRODUCTS:
        rows.append({
            "item_id": p["item_id"],
            "title": p["title"],
            "description": p["description"],
            "url": product_url(p),
            "image_url": p["image"],
            "additional_image_urls": ",".join(p["extra_images"]),
            "price": "0.00 USD",
            "availability": "in_stock",
            "condition": "new",
            "brand": FIRM,
            "product_category": "Services > Legal Services > Personal Injury Law",
            "seller_name": FIRM,
            "seller_url": SITE + "/",
            "seller_privacy_policy": f"{SITE}/privacy-policy/",
            "seller_tos": f"{SITE}/disclaimer/",
            "is_eligible_search": True,
            "is_eligible_checkout": False,
            "target_countries": "US",
            "store_country": "US",
        })
    return rows


def write_feeds():
    FEED_DIR.mkdir(exist_ok=True)
    rows = feed_rows()
    fields = list(rows[0].keys())

    def flat(v):
        return str(v).lower() if isinstance(v, bool) else v

    with gzip.open(FEED_DIR / "bam-products.jsonl.gz", "wt", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    for name, opener in (("bam-products.csv", open), ("bam-products.csv.gz", gzip.open)):
        with opener(FEED_DIR / name, "wt", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: flat(v) for k, v in r.items()})

    # Tab-separated .txt (header row + one product per row).
    with open(FEED_DIR / "bam-products.txt", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: flat(v) for k, v in r.items()})

    import pyarrow as pa
    import pyarrow.parquet as pq
    pq.write_table(pa.Table.from_pylist(rows), FEED_DIR / "bam-products.parquet", compression="zstd")


# --- Page ---------------------------------------------------------------------
CSS = """
.bamp{--navy:#05476b;--navy-deep:#063e57;--gold:#b99e5a;--gold-dark:#8a6d1f;--ink:#404040;--line:#e3e7ea;--wash:#f4f7f9;
  color:var(--ink);font-family:Sunflower,Inter,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;line-height:1.55;font-size:17px}
.bamp *{box-sizing:border-box}
.bamp-wrap{max-width:1160px;margin:0 auto;padding:0 20px}
.bamp h1,.bamp h2,.bamp h3{font-family:Georgia,"Times New Roman",serif;color:var(--navy);line-height:1.15;margin:0;font-weight:400;text-wrap:balance}
.bamp-hero{background:var(--navy);color:#fff;padding:56px 0 60px}
.bamp-eyebrow{color:var(--gold);font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:14px;margin:0 0 14px}
.bamp-hero h1{color:#fff;font-size:clamp(34px,5vw,54px);max-width:17ch}
.bamp-hero p.bamp-lede{max-width:60ch;margin:18px 0 28px;font-size:19px;color:#e6eef2}
.bamp-cta{display:flex;flex-wrap:wrap;gap:12px}
.bamp-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:50px;padding:12px 22px;border-radius:3px;
  font-weight:700;font-size:16px;letter-spacing:.03em;text-transform:uppercase;text-decoration:none;border:2px solid transparent;transition:background .15s,color .15s,border-color .15s}
.bamp-btn-gold{background:var(--gold);color:#fff;border-color:var(--gold)}
.bamp-btn-gold:hover{background:var(--gold-dark);border-color:var(--gold-dark);color:#fff}
.bamp-btn-navy{background:var(--navy);color:#fff;border-color:var(--navy)}
.bamp-btn-navy:hover{background:var(--navy-deep);color:#fff}
.bamp-btn-ghost{background:transparent;color:#fff;border-color:#fff}
.bamp-btn-ghost:hover{background:#fff;color:var(--navy)}
.bamp-btn:focus-visible{outline:3px solid var(--gold);outline-offset:3px}
.bamp-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:26px;padding:52px 0 16px}
.bamp-card{display:flex;flex-direction:column;background:#fff;border:1px solid var(--line);border-top:4px solid var(--gold);scroll-margin-top:120px}
.bamp-card:target{box-shadow:0 0 0 3px var(--gold)}
.bamp-card img{display:block;width:100%;height:auto;aspect-ratio:3/2;object-fit:cover;background:var(--wash)}
.bamp-body{display:flex;flex-direction:column;flex:1;padding:22px 22px 24px}
.bamp-price{align-self:flex-start;background:var(--wash);color:var(--navy);font-weight:700;font-size:13px;letter-spacing:.06em;text-transform:uppercase;padding:4px 10px;margin-bottom:12px}
.bamp-card h2{font-size:25px}
.bamp-tag{margin:8px 0 12px;font-weight:700;color:var(--gold-dark)}
.bamp-desc{margin:0 0 14px;font-size:16px}
.bamp-card ul{margin:0 0 20px;padding:0;list-style:none;font-size:16px}
.bamp-card li{position:relative;padding:5px 0 5px 22px}
.bamp-card li::before{content:"";position:absolute;left:2px;top:14px;width:9px;height:9px;background:var(--gold);transform:rotate(45deg)}
.bamp-card .bamp-cta{margin-top:auto;flex-direction:column}
.bamp-card .bamp-btn{width:100%}
.bamp-form{background:var(--wash);margin-top:44px;padding:52px 0;scroll-margin-top:100px}
.bamp-form-in{display:grid;grid-template-columns:1fr 1.2fr;gap:44px;align-items:start}
.bamp-form h2{font-size:clamp(28px,3.4vw,38px)}
.bamp-form p{margin:14px 0}
.bamp-phone{display:inline-block;font-family:Georgia,serif;font-size:32px;color:var(--navy);text-decoration:none;font-variant-numeric:tabular-nums}
.bamp-formbox{background:#fff;border:1px solid var(--line);padding:26px}
.bamp-fine{padding:26px 0 44px;font-size:13.5px;color:#5d6468}
.bamp-fine p{margin:0 0 8px;max-width:95ch}
@media (max-width:900px){.bamp-grid{grid-template-columns:1fr;max-width:560px;margin:0 auto}.bamp-form-in{grid-template-columns:1fr;gap:26px}}
@media (prefers-reduced-motion:reduce){.bamp-btn{transition:none}}
"""

PHONE_ICON = ('<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 '
              '11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z"/></svg>')


def e(s):
    return html.escape(s, quote=True)


def json_ld():
    return json.dumps({
        "@context": "https://schema.org",
        "@graph": [{
            "@type": "Service",
            "@id": f"{PAGE_URL}#{p['slug']}",
            "name": p["title"],
            "description": p["description"],
            "image": p["image"],
            "url": product_url(p),
            "serviceType": "Personal injury legal services",
            "areaServed": [{"@type": "State", "name": "Utah"}, {"@type": "State", "name": "Idaho"}],
            "provider": {"@type": "LegalService", "name": FIRM, "url": SITE + "/", "telephone": PHONE_TEL},
            "offers": {"@type": "Offer", "price": "0.00", "priceCurrency": "USD",
                       "availability": "https://schema.org/InStock", "url": product_url(p)},
        } for p in PRODUCTS],
    }, ensure_ascii=False, indent=1)


def card(p):
    bullets = "".join(f"<li>{e(b)}</li>" for b in p["bullets"])
    # Strip the trailing "Submit ... or call" sentence from the card copy; the buttons do that job.
    desc = p["description"].rsplit(". ", 2)[0] + "."
    return f"""
    <article class="bamp-card" id="{p['slug']}">
      <img src="{e(p['image'])}" alt="{e(p['image_alt'])}" width="1200" height="800" loading="lazy">
      <div class="bamp-body">
        <span class="bamp-price">Free &middot; $0</span>
        <h2>{e(p['title'])}</h2>
        <p class="bamp-tag">{e(p['tagline'])}</p>
        <p class="bamp-desc">{e(desc)}</p>
        <ul>{bullets}</ul>
        <div class="bamp-cta">
          <a class="bamp-btn bamp-btn-gold" href="#bam-contact" data-service="{e(p['title'])}">Send My Contact Info</a>
          <a class="bamp-btn bamp-btn-navy" href="tel:{PHONE_TEL}">{PHONE_ICON} Call Now {PHONE_DISPLAY}</a>
        </div>
      </div>
    </article>"""


def body(form_html):
    cards = "".join(card(p) for p in PRODUCTS)
    return f"""<div class="bamp">
<style>{CSS}</style>
<script type="application/ld+json">
{json_ld()}
</script>
  <section class="bamp-hero">
    <div class="bamp-wrap">
      <p class="bamp-eyebrow">Free consultations | No fee unless we win</p>
      <h1>How we can help after an injury</h1>
      <p class="bamp-lede">Three ways to get started with {FIRM}. Each one is free. Pick one, send us your contact information, or call now.</p>
      <div class="bamp-cta">
        <a class="bamp-btn bamp-btn-gold" href="#bam-contact">Send My Contact Info</a>
        <a class="bamp-btn bamp-btn-ghost" href="tel:{PHONE_TEL}">{PHONE_ICON} Call Now {PHONE_DISPLAY}</a>
      </div>
    </div>
  </section>
  <div class="bamp-wrap">
    <div class="bamp-grid">{cards}
    </div>
  </div>
  <section class="bamp-form" id="bam-contact">
    <div class="bamp-wrap bamp-form-in">
      <div>
        <p class="bamp-eyebrow" style="color:var(--gold-dark)">Get started</p>
        <h2>Tell us how to reach you</h2>
        <p>Send your contact information and a member of our team will follow up about your claim. It is free and confidential.</p>
        <p>Prefer to call?<br><a class="bamp-phone" href="tel:{PHONE_TEL}">{PHONE_DISPLAY}</a></p>
      </div>
      <div class="bamp-formbox">{form_html}</div>
    </div>
  </section>
  <div class="bamp-wrap bamp-fine">
    <p>Attorney advertising. Services are offered for personal injury claims in Utah and Idaho. Submitting your information or calling does not create an attorney-client relationship; representation begins only when you and the firm sign a written fee agreement.</p>
    <p>&ldquo;Free&rdquo; means there is no charge for the evaluation or consultation and no upfront cost. If the firm represents you, attorney fees are contingent on a recovery and are a percentage of it; case costs may be deducted from the recovery as described in the fee agreement. A letter to an insurance company is sent only after the firm agrees to represent you. Every case is different, and past results do not guarantee a similar outcome.</p>
  </div>
</div>
"""


def write_pages():
    # 1) WordPress snippet: paste into a Code Block / Custom HTML block on the /products/ page.
    snippet = ("<!-- BAM products page. Generated by build.py; edit there and re-run. -->\n"
               + body(FORM_SHORTCODE))
    (HERE / "products-wordpress.html").write_text(snippet, encoding="utf-8")

    # 2) Standalone page: preview, or upload as a static file. The form button goes to /contact/.
    fallback_form = (f'<p style="margin-top:0">Use our secure consultation request form.</p>'
                     f'<a class="bamp-btn bamp-btn-gold" style="width:100%" href="{CONTACT_URL}">Open the Contact Form</a>')
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Free Case Evaluation, Consultation &amp; Insurance Letter | {FIRM}</title>
<meta name="description" content="Free case evaluation, free consultation, and a strongly-worded letter to the insurance company from {FIRM}. Utah and Idaho. Call {PHONE_DISPLAY}.">
<link rel="canonical" href="{PAGE_URL}">
<style>body{{margin:0;background:#fff}}.bamp-top{{padding:18px 20px;max-width:1160px;margin:0 auto}}.bamp-top img{{height:56px;width:auto;display:block}}</style>
</head>
<body>
<header class="bamp-top"><a href="{SITE}/"><img src="{LOGO}" alt="{FIRM}" width="353" height="83"></a></header>
{body(fallback_form)}</body>
</html>
"""
    (HERE / "products.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    write_feeds()
    write_pages()
    print("Wrote:", ", ".join(sorted(str(p.relative_to(HERE)) for p in list(FEED_DIR.iterdir()) + [HERE / "products.html", HERE / "products-wordpress.html"])))
