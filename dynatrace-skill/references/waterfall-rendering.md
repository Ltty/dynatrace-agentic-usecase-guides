# Waterfall Rendering Recipe

How to present beat 4's chained trace query as a condensed call waterfall.

The raw query returns all spans for one trace — typically 10–20 rows. Condense to 3–4
meaningful rows showing only the critical path plus clean-sibling summary lines.

---

## What the query returns

The waterfall query returns these fields per span:

| Field | Meaning |
|---|---|
| `span.id` | Unique span identifier |
| `span.parent_id` | Parent span's ID (null for root) |
| `start_time` | When this span started |
| `service` | Service that produced this span |
| `span_name` | Operation name |
| `duration_ms` | Duration in milliseconds |
| `failed` | Boolean — true if this span failed |
| `status` | Status code (e.g. "error") |

---

## Build the tree

1. Sort spans by `start_time` ascending.
2. Group by parentage: span whose `parent_id` is null (or has no match in the result set) is
   the root. Assign each span's depth by how many hops up the parent chain reach the root.
3. **Orphan spans** — spans whose `parent_id` points at a span not in the result set (mixed
   OneAgent/OTel instrumentation is common): assign them to the smallest span whose
   `[start_time, start_time + duration_ms]` interval contains them. This is the time-containment
   fallback.

---

## What to show

Show **only the critical path** — the chain from root to the failing span — plus one summary
line for each group of clean siblings. Do not dump all rows.

**Format each row as:**

```text
  [indent]  service / span_name   duration_ms ms   [FAILED] or ok
```

Where indent is two spaces per depth level.

**Example condensed output (illustrative):**

```text
  frontend / HTTP GET /checkout                42ms   ok
    checkout / PlaceOrder                      38ms   ok
      checkout also called: cart, catalog, currency, shipping, quote — all clean
      payment / Charge                         714ms  FAILED
```

The "also called" summary line collapses the clean downstream calls into one line. This covers
the "everything upstream was clean" finding without listing 10 rows.

---

## Condensing rules

1. **Show every span on the path from root to the failing span.** Do not collapse these.
2. **For siblings of any node on the critical path:** if all are successful (`failed != true`),
   collapse into one summary line: `"[parent service] also called: [span_name1], [span_name2], ... — all clean"`
3. **Show the failing span last** with the `FAILED` marker. If more than one span failed,
   show each individually — multiple failures are themselves a finding.
4. **Keep the output to 3–5 rows** (plus the summary line). If the critical path is longer
   than 4 hops, show the root, the failing hop, and any hop directly adjacent to the failure.
   Collapse the middle of long clean chains the same way as siblings.
