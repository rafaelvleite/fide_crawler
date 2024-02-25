import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def plot_rating_time_series(games_df, localization_data):
    if not games_df.empty:
        games_df['date'] = pd.to_datetime(games_df['date'])
        games_df['player_rating'] = pd.to_numeric(games_df['player_rating'], errors='coerce')
        games_df.sort_values('date', inplace=True)

        plt.figure(figsize=(10, 4))
        plt.plot(games_df['date'], games_df['player_rating'], marker='o', linestyle='-')

        plt.title(localization_data['classic_rating_over_time'])
        plt.xlabel(localization_data['date'])
        plt.ylabel(localization_data['classic_rating'])
        plt.grid(True)
        plt.tight_layout()
        st.pyplot(plt)
    else:
        st.write(localization_data['no_rating_data_available'])


def create_pie_chart(sizes, labels, title):
    # Define the colors for the pie chart
    colors = ['#77dd77', '#fdfd96', '#ff6961']  # Pastel green, pastel yellow, pastel red
    
    # Create a pie chart
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=[label for label in labels], autopct='%1.1f%%', startangle=90, colors=colors)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    
    # Set the title of the chart
    plt.title(title)
    
    return fig

# Função Aprimorada para Criar um Gráfico de Barras
def create_enhanced_bar_chart(values, categories, title, localization_data):
    fig, ax = plt.subplots(figsize=(16, 6))
    colors = ['#add8e6',  # Pastel blue
              '#77dd77',  # Pastel green
              '#fdfd96',  # Pastel yellow
              '#ff6961',  # Pastel red
              '#68c973',  # Saturated green
              '#fcf75e',  # Saturated yellow
              '#ff5f5f']  # Saturated red
    ax.set_ylabel(localization_data['avg_opponent_rating'])
    ax.set_title(title)
    plt.xticks(rotation=45)
    for i, v in enumerate(values):
        ax.text(i, v + 3, f"{v:.0f}", ha='center', va='bottom')
    return fig

