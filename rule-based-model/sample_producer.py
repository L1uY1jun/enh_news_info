import copy
import os
import json
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image

from ecaption_utils.kafka.faust import get_faust_app, initialize_topics, FaustApplication, get_error_handler
from ecaption_utils.kafka.topics import Topic, get_event_type

SAMPLE_IMAGE_PATH = ".\\Infographic_Generator\\rule_based_model\\sample_images"

sample_data_without_visual_short = {
    "title": "The Future of Renewable Energy",
    "excerpt": "As the world moves toward sustainable energy sources, renewable energy technologies are rapidly evolving",
    "graph": {
        "nodes": [
            ("Renewable Energy", {"occurence": 1278}),
            ("Solar Energy", {"occurence": 852}),
            ("Wind Energy", {"occurence": 612}),
            ("Geothermal Energy", {"occurence": 862}),
            ("Hydro Energy", {"occurence": 931}),
            ("Bioenergy", {"occurence": 134}),
            ("Electricity Generation", {"occurence": 648})
        ],
        "edges": [
            ("Renewable Energy", "Solar Energy", {"relation": "includes"}),
            ("Renewable Energy", "Wind Energy", {"relation": "includes"}),
            ("Renewable Energy", "Geothermal Energy", {"relation": "includes"}),
            ("Renewable Energy", "Hydro Energy", {"relation": "includes"}),
            ("Renewable Energy", "Bioenergy", {"relation": "includes"}),
            ("Solar Energy", "Electricity Generation", {"relation": "produces"}),
            ("Wind Energy", "Electricity Generation", {"relation": "produces"}),
            ("Geothermal Energy", "Electricity Generation", {"relation": "produces"}),
            ("Hydro Energy", "Electricity Generation", {"relation": "produces"}),
            ("Bioenergy", "Electricity Generation", {"relation": "produces"})
        ]
    },
    "related_facts": [
        "Renewable energy sources accounted for 29% of global electricity generation in 2023.",
        "The solar power industry has seen a 20% annual growth rate over the past five years.",
        "Investments in renewable energy technologies exceeded $500 billion in 2023.",
        "Over 1 million jobs have been created in the renewable energy sector globally in the last year.",
        "Wind energy capacity reached 1,000 GW globally in 2023, making it one of the fastest-growing energy sources.",
        "Geothermal energy has the potential to provide up to 15% of the world's electricity by 2050.",
        "Bioenergy accounted for 5% of total U.S. energy consumption in 2022, with significant growth expected.",
        "The cost of solar panels has dropped by 89% since 2010, making solar energy more accessible."
    ]
}

sample_data_without_visual_long = {
    "title": "The Evolution of Artificial Intelligence in Healthcare",
    "excerpt": (
        "Artificial Intelligence (AI) is transforming healthcare by enhancing diagnostic accuracy, streamlining tasks, and enabling personalized treatments. As AI evolves, it drives innovations in drug discovery and remote patient care, though ethical and integration challenges remain."
    ),
    "graph": {
        "nodes": [
            ("Artificial Intelligence", {"occurence": 1000}),
            ("Diagnostics", {"occurence": 400}),
            ("Drug Discovery", {"occurence": 350}),
            ("Telemedicine", {"occurence": 300}),
            ("Wearable Devices", {"occurence": 250}),
            ("Administrative Tasks", {"occurence": 150}),
            ("Clinical Trials", {"occurence": 200}),
            ("Data Privacy", {"occurence": 100}),
            ("Healthcare Providers", {"occurence": 120}),
            ("Patients", {"occurence": 150})
        ],
        "edges": [
            ("Artificial Intelligence", "Diagnostics", {"relation": "enhances"}),
            ("Artificial Intelligence", "Drug Discovery", {"relation": "accelerates"}),
            ("Artificial Intelligence", "Telemedicine", {"relation": "enables"}),
            ("Artificial Intelligence", "Wearable Devices", {"relation": "integrates"}),
            ("Artificial Intelligence", "Administrative Tasks", {"relation": "automates"}),
            ("Artificial Intelligence", "Clinical Trials", {"relation": "optimizes"}),
            ("Artificial Intelligence", "Data Privacy", {"relation": "challenges"}),
            ("Wearable Devices", "Patients", {"relation": "monitors"}),
            ("Telemedicine", "Patients", {"relation": "connects"}),
            ("Healthcare Providers", "Diagnostics", {"relation": "benefit from"}),
            ("Healthcare Providers", "Administrative Tasks", {"relation": "simplifies"})
        ]
    },
    "related_facts": [
        "AI in healthcare is projected to grow from $11.4 billion in 2021 to over $188 billion by 2030.",
        "AI-powered diagnostics can reduce diagnostic errors by up to 25%, leading to more accurate patient outcomes.",
        "Over 40% of healthcare providers use AI to help with scheduling and administrative tasks, reducing human error and saving time.",
        "AI-driven drug discovery has accelerated research, with algorithms identifying potential compounds in a fraction of the time previously required.",
        "Wearable devices equipped with AI algorithms are being used to monitor patient vitals in real time, allowing for quicker intervention in emergencies.",
        "AI in telemedicine has helped increase access to healthcare, particularly in remote and underserved regions.",
        "By 2025, it is estimated that 50% of clinical trials will be conducted using AI to enhance participant recruitment and data analysis.",
        "The global shortage of healthcare workers may be mitigated by AI, with automation handling routine tasks, allowing professionals to focus on patient care.",
        "Natural Language Processing (NLP) models are being used to analyze medical literature and patient data, providing clinicians with insights that improve decision-making.",
        "Concerns about data privacy and algorithmic bias remain critical issues that need to be addressed to ensure AI's ethical deployment in healthcare."
    ]
}

def generate_sample_data_with_visual_short():
    image_path = SAMPLE_IMAGE_PATH + "\\sample_img1.png"
    image = Image.open(image_path)
    sample_data_copy = copy.deepcopy(sample_data_without_visual_short)
    sample_data_copy['image'] = image
    return sample_data_copy

def generate_sample_data_with_visual_long():
    image_path = SAMPLE_IMAGE_PATH + "\\sample_img2.png"
    image = Image.open(image_path)
    sample_data_copy = copy.deepcopy(sample_data_without_visual_long)
    sample_data_copy['image'] = image
    return sample_data_copy

Event = get_event_type(Topic.INFORMATION_QUERYING_RESULTS)
sample_query_event_short = Event(
    request_id=0,
    url="https://www.example.com/the-future-of-renewable-energy",
    title="The Future of Renewable Energy",
    description="As the world moves toward sustainable energy sources, renewable energy technologies are rapidly evolving.",
    image="https://sequoiares.org/_next/image?url=%2Fimages%2Ftypes-pf-renewable-energy.jpg&w=384&q=75",
    related_articles=[
        {
            "url": "https://www.example.com/solar-energy-growth",
            "title": "The Rapid Growth of Solar Energy",
            "image": "https://www.example.com/images/solar-energy.jpg",
            "description": "Exploring the exponential growth of solar energy and its impact on the renewable energy landscape.",
            "similarity": 89.3
        },
        {
            "url": "https://www.example.com/wind-energy-expansion",
            "title": "Wind Energy: Expanding Horizons",
            "image": "https://www.example.com/images/wind-energy.jpg",
            "description": "How wind energy has become one of the fastest-growing renewable energy sources globally.",
            "similarity": 87.5
        }
    ],
    related_facts=[
        "Renewable energy sources accounted for 29% of global electricity generation in 2023.",
        "The solar power industry has seen a 20% annual growth rate over the past five years.",
        "Investments in renewable energy technologies exceeded $500 billion in 2023.",
        "Over 1 million jobs have been created in the renewable energy sector globally in the last year.",
        "Wind energy capacity reached 1,000 GW globally in 2023, making it one of the fastest-growing energy sources.",
        "Geothermal energy has the potential to provide up to 15% of the world's electricity by 2050.",
        "Bioenergy accounted for 5% of total U.S. energy consumption in 2022, with significant growth expected.",
        "The cost of solar panels has dropped by 89% since 2010, making solar energy more accessible."
    ],
    adjlist={
        "1": [
            [2, 1001],
            [3, 1002],
            [4, 1003],
            [5, 1004],
            [6, 1005]
        ],
        "2": [
            [7, 2001]
        ],
        "3": [
            [7, 2001]
        ],
        "4": [
            [7, 2001]
        ],
        "5": [
            [7, 2001]
        ],
        "6": [
            [7, 2001]
        ],
        "7": []
    },
    node_occurrences={
        "1": 12,
        "2": 8,
        "3": 6,
        "4": 9,
        "5": 9,
        "6": 1,
        "7": 6
    },
    entity_labels={
        "1": "Renewable Energy",
        "2": "Solar Energy",
        "3": "Wind Energy",
        "4": "Geothermal Energy",
        "5": "Hydro Energy",
        "6": "Bioenergy",
        "7": "Electricity Generation"
    },
    property_labels={
        "1001": "includes",
        "1002": "includes",
        "1003": "includes",
        "1004": "includes",
        "1005": "includes",
        "2001": "produces"
    }
)

sample_query_event_long = Event(
    request_id=1,
    url="https://www.example.com/the-evolution-of-artificial-intelligence-in-healthcare",
    title="The Evolution of Artificial Intelligence in Healthcare",
    description="Artificial Intelligence (AI) is transforming healthcare by enhancing diagnostic accuracy, streamlining tasks, and enabling personalized treatments. As AI evolves, it drives innovations in drug discovery and remote patient care, though ethical and integration challenges remain.",
    image="https://framerusercontent.com/images/FnY8YV27DFGHc5jP5kre2NV7A0.jpeg",
    related_articles=[
        {
            "url": "https://www.example.com/ai-in-diagnostics",
            "title": "AI in Diagnostics: Revolutionizing Healthcare",
            "image": "https://www.example.com/images/ai-diagnostics.jpg",
            "description": "AI-powered diagnostics reduce errors and improve outcomes, driving the future of healthcare.",
            "similarity": 85.6
        }
    ],
    related_facts=[
        "AI in healthcare is projected to grow from $11.4 billion in 2021 to over $188 billion by 2030.",
        "AI-powered diagnostics can reduce diagnostic errors by up to 25%, leading to more accurate patient outcomes.",
        "Over 40% of healthcare providers use AI to help with scheduling and administrative tasks, reducing human error and saving time.",
        "AI-driven drug discovery has accelerated research, with algorithms identifying potential compounds in a fraction of the time previously required.",
        "Wearable devices equipped with AI algorithms are being used to monitor patient vitals in real time, allowing for quicker intervention in emergencies.",
        "AI in telemedicine has helped increase access to healthcare, particularly in remote and underserved regions.",
        "By 2025, it is estimated that 50% of clinical trials will be conducted using AI to enhance participant recruitment and data analysis.",
        "The global shortage of healthcare workers may be mitigated by AI, with automation handling routine tasks, allowing professionals to focus on patient care.",
        "Natural Language Processing (NLP) models are being used to analyze medical literature and patient data, providing clinicians with insights that improve decision-making.",
        "Concerns about data privacy and algorithmic bias remain critical issues that need to be addressed to ensure AI's ethical deployment in healthcare."
    ],
    adjlist={
        "21": [
            [39563, 37291],
            [5829314, 59273],
            [7382, 1827364],
            [160439, 64739],
            [8927356, 103],
            [497281, 1938472],
            [63071, 48301]
        ],
        "39563": [],
        "5829314": [],
        "7382": [
            [904652, 9386]
        ],
        "160439": [
            [904652, 2038475]
        ],
        "8927356": [],
        "497281": [],
        "63071": [],
        "295": [
            [39563, 37481],
            [8927356, 35]
        ],
        "904652": []
    },
    node_occurrences={
        "21": 10,
        "39563": 4,
        "5829314": 4,
        "7382": 3,
        "160439": 3,
        "8927356": 2,
        "497281": 2,
        "63071": 1,
        "295": 1,
        "904652": 2
    },
    entity_labels={
        "21": "Artificial Intelligence",
        "39563": "Diagnostics",
        "5829314": "Drug Discovery",
        "7382": "Telemedicine",
        "160439": "Wearable Devices",
        "8927356": "Administrative Tasks",
        "497281": "Clinical Trials",
        "63071": "Data Privacy",
        "295": "Healthcare Providers",
        "904652": "Patients"
    },
    property_labels={
        "37291": "enhances",
        "59273": "accelerates",
        "1827364": "enables",
        "64739": "integrates",
        "103": "automates",
        "1938472": "optimizes",
        "48301": "challenges",
        "2038475": "monitors",
        "9386": "connects",
        "37481": "benefit from",
        "35": "simplifies"
    }
)
