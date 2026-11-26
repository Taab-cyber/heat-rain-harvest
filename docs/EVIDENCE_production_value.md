# Production, value and food equivalent: how each figure was reached

This note explains every number in the atlas's "Production and value, 2022-23" section and the
For experts → Production and value tab. Each claim gives its source (document, table, page), the
arithmetic, and the check it passed. Where a check failed, the figure is not shown and the reason
is stated. Code: `src/official_stats.py` (reads the official tables), `src/production_value.py`
(checks and calculations), tests in `tests/test_production_value.py`. Decision record: DECISIONS D25.

Season covered: **2022-23** (wheat sown November 2022, harvested March-April 2023; kharif rice
sown June 2022). It is the last season in our crop data.

---

## 1. Sources

All files are in `data/raw/official/`, unedited, and in the project's data release.

| Used for | Document | Table and page | SHA-256 (first 12) |
|---|---|---|---|
| Official production by state and all-India | *Agricultural Statistics at a Glance 2024*, Directorate of Economics and Statistics, Ministry of Agriculture and Farmers Welfare | Rice: Tables 2.4(a) p.47-48, 2.4(b) p.49. Wheat: Tables 2.5(a) p.50-51, 2.5(b) p.52 | `1481bff6f80b` |
| Minimum Support Price | same | Table 2.71, p.169 | same |
| Cost of production by state | same (source CACP) | Table 2.73(a), p.171 | same |
| Grain available per person | same | Table 3.6, p.188 | same |
| Rural share of population | same (source Registrar General of India) | Table 1.1(a), p.21 | same |
| Cereals eaten per person (cross-check) | *Household Consumption Expenditure Survey 2023-24*, NSS Report 592, MoSPI | Tables 3.7 (p.52), 3.8R (p.53), 3.8U (p.54) | `368deb9c858d` |
| Rice to paddy conversion | Comptroller and Auditor General, Report No. 31 of 2015, *Procurement and Milling of Paddy for Central Pool*, chapter 2 | footnote 17, p.1 of the chapter | `e9b25c8a83b0` |
| District production | DES Area-Production-Yield portal (data.desagri.gov.in), downloaded for this project | `data/raw/apy/` | in data release |

The page numbers are PDF page numbers. Every table is read by code from the PDF; the code stops with an
error if a self-check fails (for example, each state's "% of All-India" must equal its production divided
by the all-India production within 0.1 points, and each year's yield must equal production divided by area
within 2%). All checks passed.

---

## 2. Finding: the district figures do not always add up to the official totals

**Claim.** Summing the district production that the DES portal provides gives a higher all-India total than
the official figure in most recent years, and the gap is concentrated in a few states.

**Evidence, all-India** (million tonnes; ours = sum of all district rows, all seasons):

| Season | Wheat official | Wheat ours | Gap | Rice official | Rice ours | Gap |
|---|---|---|---|---|---|---|
| 2014-15 | 86.53 | 84.87 | −1.9% | 105.48 | 114.71 | +8.8% |
| 2015-16 | 92.29 | 94.39 | +2.3% | 104.41 | 101.78 | −2.5% |
| 2016-17 | 98.51 | 113.46 | +15.2% | 109.70 | 118.92 | +8.4% |
| 2018-19 | 103.60 | 119.43 | +15.3% | 116.48 | 118.67 | +1.9% |
| 2019-20 | 107.86 | 132.34 | +22.7% | 118.87 | 134.95 | +13.5% |
| 2022-23 | 110.55 | 128.48 | +16.2% | 135.76 | 154.95 | +14.1% |

Full series: `data/processed/value/all_india_series.csv`, chart in the app.

**Evidence, by state, 2022-23** (million tonnes; official = Tables 2.4(b) and 2.5(b)):

| Crop | State | Official | Ours | Gap | Passes (±5%) |
|---|---|---|---|---|---|
| Wheat | Uttar Pradesh | 33.61 | 38.07 | +13.3% | no |
| Wheat | Madhya Pradesh | 22.73 | 34.98 | +53.9% | no |
| Wheat | Punjab | 16.78 | 16.57 | −1.3% | yes |
| Wheat | Haryana | 10.93 | 11.06 | +1.2% | yes |
| Wheat | Rajasthan | 10.64 | 11.32 | +6.4% | no |
| Wheat | Bihar | 6.51 | 6.60 | +1.4% | yes |
| Wheat | Gujarat | 3.46 | 4.10 | +18.6% | no |
| Wheat | Maharashtra | 2.37 | 2.30 | −2.9% | yes |
| Wheat | Uttarakhand | 0.83 | 0.83 | +0.1% | yes |
| Wheat | Himachal Pradesh | 0.59 | 0.61 | +3.3% | yes |
| Wheat | Other states (all-India minus the above) | 2.10 | 2.04 | −3.1% | yes |
| Rice | Telangana | 15.88 | 17.21 | +8.4% | no |
| Rice | Uttar Pradesh | 16.14 | 16.56 | +2.6% | yes |
| Rice | West Bengal | 15.48 | 15.84 | +2.3% | yes |
| Rice | Punjab | 12.99 | 13.75 | +5.9% | no |
| Rice | Chhattisgarh | 9.81 | 11.22 | +14.4% | no |
| Rice | Odisha | 8.25 | 11.93 | +44.6% | no |
| Rice | Bihar | 7.02 | 7.87 | +12.1% | no |
| Rice | Andhra Pradesh | 7.94 | 8.42 | +6.0% | no |
| Rice | Madhya Pradesh | 7.02 | 13.13 | +87.0% | no |
| Rice | Tamil Nadu | 7.56 | 7.56 | 0.0% | yes |
| Rice | Other states | 27.67 | 31.46 | +13.7% | no |

**It is not our processing.** The raw portal download already sums to these values (for example 132.34 Mt of
wheat in 2019-20 before any of our steps), no season is counted twice (wheat is almost entirely "Rabi"), and
our harmonisation to Census 2011 districts keeps totals unchanged.

---

## 3. Finding: what the gaps are, where the data allow us to tell

Comparing area and yield as well as production (2022-23, ours ÷ official):

| Crop, state | Production | Area | Yield | Reading |
|---|---|---|---|---|
| Rice, Odisha | 1.446 | 1.001 | 1.446 | Area matches; production and yield are 1.45 times higher. One tonne of rice comes from 1/0.67 = 1.49 tonnes of paddy, so the district figures are most likely paddy, not rice. |
| Rice, Madhya Pradesh | 1.870 | 1.128 | 1.658 | Yield far too high. The state's district yield jumps from 2,282 to 3,411 kg/ha between 2021-22 and 2022-23 (+49%), consistent with a switch to paddy in that year, plus an area difference. |
| Wheat, Madhya Pradesh | 1.539 | 1.368 | 1.125 | Mostly an area difference: the reporting break already found in 2018 (DECISIONS D15). |
| Wheat, Uttar Pradesh | 1.133 | 1.071 | 1.058 | Area and yield both a little high. |
| Wheat, Gujarat | 1.186 | 1.208 | 0.977 | Area too high; yield correct. |
| Wheat, Punjab | 0.987 | 0.996 | 0.992 | Matches. |
| Rice, Tamil Nadu | 1.000 | 0.999 | 1.000 | Matches. |

What we **cannot** tell from public data: why the portal's district figures differ from the state figures the
same Directorate publishes (different estimate rounds, paddy versus rice in some district reports, or
revisions that reached state tables but not district rows). We report the gap; we do not guess the cause beyond
what area and yield show.

---

## 4. The rule used in the atlas

1. A state "passes" if our district sum is within **±5%** of the official state total for 2022-23. States outside
   the major-state tables are checked together against the official remainder (all-India minus major states).
2. For districts in a state that passes: production, value, margin and food equivalent are shown.
3. For districts in a state that fails: **nothing is shown** except the reason and the two totals. (Example:
   Indore, wheat: "For Madhya Pradesh, the district figures on the DES portal add up to 34.98 million tonnes, but
   the official state total is 22.73 million tonnes ... We only show district figures that add up to the
   official total.")
4. India-level figures use the **official** totals only, never our district sums.

Result for 2022-23: 252 of 487 wheat districts and 121 of 564 rice districts pass (six more are held back because the district spans two states or its state could not be identified). Their production is 39.2 Mt of
wheat and 40.0 Mt of rice. Tested in `tests/test_production_value.py` and by running the app headless for Indore
(MP, wheat), Cuttack (Odisha, rice) and Ludhiana (Punjab, wheat).

---

## 5. Value at the Minimum Support Price

**Prices** (Table 2.71, crop year 2022-23): wheat ₹2,125 per quintal; paddy (common) ₹2,040 per quintal.
The crop-year column is the season the crop was grown in; wheat grown in 2022-23 is bought in the 2023-24
marketing season at ₹2,125.

**Rice is valued as paddy** because MSP is fixed for paddy and production is reported as rice. The conversion
is the official out-turn ratio: "Out-turn Ratio of production of 67 per cent of raw rice ... out of one quintal
paddy" (CAG Report 31 of 2015, chapter 2, footnote 17; recommended by the Gokak Committee, 1994). So
paddy = rice ÷ 0.67. The code only returns 0.67 if that sentence is found in the downloaded report.

**India, 2022-23** (official production; 1 tonne = 10 quintals; 1 crore = 10 million):

- Wheat: 110.55 million t × 10 × ₹2,125 = ₹2,34,919 crore.
- Rice: 135.76 million t ÷ 0.67 × 10 = 2,026.3 million quintals of paddy × ₹2,040 = ₹4,13,359 crore.

This is the value **if every quintal were sold at MSP**. In practice many farmers sell below MSP, particularly
where government procurement is limited, so it is an upper estimate of what farmers received.

---

## 6. Margin over cost

**Cost** (Table 2.73(a), source CACP): projected cost of production **A2+FL**, ₹ per quintal, by state. A2
covers all paid-out costs (seed, fertiliser, hired labour, machinery, irrigation, rent for leased land); FL adds
the value of family labour. It does not include rent on owned land or interest on owned capital (those are in
cost C2, which this table does not give). 2022-23 all-India: paddy ₹1,360, wheat ₹1,065 per quintal.

Some states have blank years in this table, so numbers were matched to year columns by their position on the
page, not by order. Check: Telangana paddy has values only from 2021-22, and Himachal Pradesh paddy from
2018-19, matching their positions in the printed table.

**Margin** = (MSP − state cost) × quintals. Per acre = margin ÷ (area in hectares × 2.4711).

- India, wheat: 1,105.5 million quintals × (2,125 − 1,065) = ₹1,17,183 crore.
- India, rice: 2,026.3 million quintals of paddy × (2,040 − 1,360) = ₹1,37,786 crore.
- Districts in states with no published cost get no margin (among verified districts: wheat in Jammu and
  Kashmir, Assam, Chandigarh and the north-eastern states).

Across verified districts the margin ranges from about ₹40 to ₹28,000 per acre for wheat (median ₹6,162; the
lowest are in Maharashtra, where the cost of ₹2,115 per quintal is almost equal to the MSP of ₹2,125), and from
₹3,334 to ₹19,579 per acre for rice (median ₹11,154).

---

## 7. Food equivalent ("how many people")

**Measure** (Table 3.6, 2022-23, financial-year basis): net availability per person per year, **rice 69.6 kg,
wheat 68.8 kg**. Net availability is production minus seed, feed and wastage, minus exports, plus imports,
plus or minus stock changes, divided by population.

**People-equivalent** = production in kg ÷ kg per person. India, 2022-23:

- Wheat: 110,550 million kg ÷ 68.8 = 161 crore people-equivalents.
- Rice: 135,760 million kg ÷ 69.6 = 195 crore people-equivalents.

Both are larger than India's population. That is expected and is the reason the atlas calls this a
"people-equivalent", not "people fed": gross production also covers exports, government stocks, seed, feed and
losses, which net availability per person has already removed. The figure says how large a harvest is in terms
people can picture, not who eats it.

**Cross-check with what households report eating** (HCES 2023-24): cereals per person per month were 9.35 kg in
villages (54.16% rice, 41.92% wheat) and 8.02 kg in towns (52.27% rice, 45.15% wheat). Weighting by the 2011
rural share of 68.85% (Table 1.1(a): 833.7 of 1,210.9 million) gives about **57.5 kg of rice and 45.9 kg of
wheat per person per year** eaten at home. These are lower than net availability (69.6 and 68.8 kg), as expected,
because they leave out food eaten outside the home and processed products. Using availability (the larger
figures) gives the smaller, more conservative people-equivalent, so the atlas uses availability.

---

## 8. Worked example: Ludhiana, wheat, 2022-23

Punjab passes the check (16.57 against an official 16.78 Mt, −1.3%).

| Step | Figure |
|---|---|
| Production (DES district data) | 1,123,400 t on 244,700 ha |
| Quintals | 1,123,400 × 10 = 11,234,000 q |
| Value at MSP | 11,234,000 × ₹2,125 = ₹2,387 crore |
| Punjab wheat cost A2+FL | ₹786 per quintal |
| Margin | 11,234,000 × (2,125 − 786) = ₹1,504 crore |
| Per acre | ₹1,504 crore ÷ (244,700 × 2.4711 = 604,678 acres) = ₹24,877 per acre |
| People-equivalent | 1,123,400,000 kg ÷ 68.8 kg = 1.63 crore |

Ludhiana's rice is not shown: Punjab's district rice figures are 5.9% above the official state total.

---

## 9. What is not claimed

- Not farmers' actual income: sales below MSP, land rent, interest and non-farm income are not included.
- Not how many people are fed: see section 7.
- Not district figures for states that fail the check, even where an individual district might be correct.
- Not years other than 2022-23 for districts: official state totals were only available to us for 2022-23 and
  2023-24, and our crop data end in 2022-23.

---

## 10. Flag for the climate analysis

The checks in section 3 also bear on the main project. The climate analysis compares each season's yield with the
district's own trend, so a constant difference in units (for example a district that always reports paddy)
cancels out. A **change** of units in the middle of the series does not. Two likely changes were found:

- Madhya Pradesh rice: state yield +49% from 2021-22 to 2022-23.
- Bihar rice: state yield +125% from 2010-11 to 2011-12.

The outlier rule (D11) only removes yields more than three times a district's median, so jumps of 1.5 to 2.2
times pass through. These seasons were checked (DECISIONS D26) with a robustness run of the monsoon-rice models that drops
Madhya Pradesh rice in 2022-23 and Bihar rice before 2011-12. This has not been run yet; it is listed in
DECISIONS D25 as an open item. The wheat results are not affected in this way: Madhya Pradesh wheat 2018+ is
already tested without (D15).

---

## 11. Reproduce

```bash
python -m src.official_stats      # reads the official tables, runs every self-check
python -m src.production_value    # state check, district values, India values
python -m src.build_db            # writes the value_* tables used by the app
python -m pytest tests/ -q        # includes tests/test_production_value.py
```
