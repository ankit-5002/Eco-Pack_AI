# 🌿 EcoPackAI: Sustainable Packaging Intelligence

**EcoPackAI** is an AI-powered sustainability intelligence platform designed to help businesses optimize packaging decisions. By analyzing material properties, costs, and environmental impact, it provides data-driven recommendations that balance profitability with eco-responsibility.

![Dashboard Preview](images/dashboard_overview.png)
*Dashboard Overview*

## 📊 Dashboard Previews

<p align="center">
  <img src="images/Index.png" width="30%" alt="Landing Page">
  &nbsp;
  <img src="images/recommend.png" width="30%" alt="Recommendation results">
  &nbsp;
  <img src="images/dashboard.png" width="30%" alt="Dashboard">
</p>

## ✨ Key Features

-   **Material Recommendation Engine**: AI-driven suggestions based on dimensions, weight, and category.
-   **Sustainability Dashboard**: Visual analytics comparing Cost vs. CO2, Biodegradability, and Recyclability.
-   **Impact Analysis**: Real-time calculation of potential CO2 reduction and cost savings.
-   **PDF Reporting**: Generate professional sustainability reports for stakeholders.
-   **Adaptive Data Layer**: Seamlessly switches between PostgreSQL database and CSV fallback for zero-config deployment.
-   **Docker Ready**: Fully containerized for easy deployment on Cloud Run, Render, or any Docker host.

## 🛠️ Tech Stack

-   **Backend**: Python, Flask
-   **Data Science**: Pandas, Scikit-learn, NumPy
-   **Visualization**: Matplotlib
-   **Database**: PostgreSQL (with CSV fallback)
-   **Deployment**: Google Cloud Run, Docker, Gunicorn

## 🚀 Quick Start

### Local Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/ecopackai.git
    cd ecopackai
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application**:
    ```bash
    python app.py
    ```
    Access the app at `http://localhost:8080`.

### 🐳 Run with Docker

To run the application in a container (recommended):

```bash
# Build and run
docker-compose up --build
```
The application will be available at `http://localhost:8080`.

## ☁️ Deployment

### Deploy on Render (Free Tier)

This project is configured for one-click deployment on Render.

1.  Push your code to GitHub.
2.  Log in to [Render](https://render.com/).
3.  Click **New +** > **Blueprints**.
4.  Connect your repository.
5.  Render will automatically detect `render.yaml` and deploy your app.

### Deploy on Google Cloud Run

1.  Build the image:
    ```bash
    gcloud builds submit --tag gcr.io/PROJECT-ID/ecopackai
    ```
2.  Deploy:
    ```bash
    gcloud run deploy ecopackai --image gcr.io/PROJECT-ID/ecopackai --platform managed --allow-unauthenticated
    ```

## 📂 Project Structure

```
├── app.py                 # Main Flask application
├── models/                # Pre-trained ML models (.pkl)
├── static/                # CSS, JS, and images
├── templates/             # HTML templates
├── materials13.csv        # Fallback dataset
├── Dockerfile             # Docker configuration
├── render.yaml            # Render deployment blueprint
└── requirements.txt       # Python dependencies
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

