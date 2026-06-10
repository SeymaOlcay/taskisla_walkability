# MBL549E – Case Study 2 (Group B)
## Ethical Web Scraping and Research Design (Wikipedia)

### Project Overview
This project collects a structured dataset from Wikipedia using ethical web scraping practices. The dataset focuses on buildings and structures by selected Italian architects and supports a basic analysis of geographical distribution and building types.

### Category and Subcategory
- **Main Category:** Buildings and structures by architect
- **Subcategory:** Buildings and structures by Italian architects

### Selected Architects
- Renzo Piano
- Carlo Maderno
- Luigi Vanvitelli
- Francesco Borromini
- Carlo Rossi
- Bernardo Antonio Vittone
- Pier Luigi Nervi
- Andrea Palladio

### Research Question
**How are the buildings of the selected Italian architects distributed geographically and by building type?**

---

## Methodology

### 1. Selection of Category and Architects
The study focused on the Wikipedia category “Buildings and structures by Italian architects.” From this category, selected architect pages were chosen in order to create a manageable and comparable dataset.

### 2. Collection of Building Links
Building page links were collected from the selected architect category pages. These links formed the main list of pages used in the scraping process.

### 3. Data Extraction
Each building page was visited individually. From these pages, the following information was extracted:

- building title
- architect name
- country
- building type
- introductory paragraphs
- first image URL
- image data

### 4. Data Cleaning and Filtering
Non-building pages, such as category pages or list pages, were excluded. Country values and building type values were also cleaned and grouped in order to make the dataset more consistent for analysis and visualization.

### 5. Dataset Construction
All extracted records were combined into a single pandas DataFrame. The final dataset was then exported as `dataset.pkl`.

### 6. Documentation and Export
To improve transparency and reproducibility, `dataDictionary.json` and `metadata.json` were also created together with the dataset.

---

## Rate Limit and Politeness Policy
Requests were sent sequentially, without parallel scraping. A 2-second delay was applied between requests using `time.sleep(2)`. In addition, a custom User-Agent header was used in order to follow politeness principles and avoid overloading Wikipedia servers.

---

## Files in This Submission
- `dataset.pkl`
- `dataDictionary.json`
- `metadata.json`
- `requirements.txt`
- `README.md`
- `GroupB_Scraper.ipynb`

---

## Data Fields
The dataset includes the following fields:
- `url`
- `title`
- `architect`
- `country`
- `building_type`
- `coordinates`
- `paragraphs`
- `first_image_url`
- `img_npy`

---

## How to Run
1. Open the notebook file in Google Colab.
2. Run all cells from top to bottom.
3. The notebook will generate the required output files.

---

## Notes and Limitations
Some Wikipedia pages do not provide fully standardized information. As a result, country and building type values may sometimes be missing, incomplete, or highly varied. In addition, not every page contains coordinates or image data.

---

## Group Members
- Merve Civcik – 523251015
- Hamdi Çakır – 523241022
- Şeyma Olcay – 523241023