import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import linregress

# Load the data
df = pd.read_csv("build_data.csv")

# Convert "Human Readable Date" and "Time of Day" to datetime for analysis
df["Date"] = pd.to_datetime(df["Human Readable Date"])
df["Time"] = pd.to_datetime(df["Time of Day"], format="%H:%M:%S").dt.time

# Combine date and time for precise timestamp analysis
df["Timestamp"] = pd.to_datetime(df["Human Readable Date"] + " " + df["Time of Day"])

# Build times in seconds for analysis
build_columns = [
    "Build src-amd64 (s)",
    "Build ovn-kubernetes-base-amd64 (s)",
    "Build ovn-kubernetes-microshift-amd64 (s)",
    "Build ovn-kubernetes-amd64 (s)",
]

# 1. Overall trends over time
def plot_trends(df, columns):
    for col in columns:
        plt.figure(figsize=(10, 6))
        sns.lineplot(x="Date", y=col, data=df, marker="o")
        plt.title(f"Trend of {col} Over Time")
        plt.xlabel("Date")
        plt.ylabel("Build Time (seconds)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show(block=False)

# 2. Correlation with day of the week
def analyze_day_of_week(df, columns):
    df["Day of Week"] = df["Date"].dt.day_name()
    for col in columns:
        plt.figure(figsize=(10, 6))
        sns.boxplot(x="Day of Week", y=col, data=df, order=[
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
        ])
        plt.title(f"Build Time Distribution by Day of Week ({col})")
        plt.xlabel("Day of Week")
        plt.ylabel("Build Time (seconds)")
        plt.tight_layout()
        plt.show(block=False)

"""
# 3. Correlation with time of day
def analyze_time_of_day(df, columns):
    df["Hour"] = pd.to_datetime(df["Time"], format="%H:%M:%S").dt.hour
    for col in columns:
        plt.figure(figsize=(10, 6))
        sns.scatterplot(x="Hour", y=col, data=df, alpha=0.7)
        plt.title(f"Build Time vs. Hour of Day ({col})")
        plt.xlabel("Hour of Day")
        plt.ylabel("Build Time (seconds)")
        plt.tight_layout()
        plt.show(block=False)
"""

def analyze_time_of_day_lineplot(df, columns):
    df["Hour"] = pd.to_datetime(df["Time"], format="%H:%M:%S").dt.hour
    for col in columns:
        hourly_avg = df.groupby("Hour")[col].mean().reset_index()
        plt.figure(figsize=(12, 6))
        sns.lineplot(x="Hour", y=col, data=hourly_avg, marker="o")
        plt.title(f"Average Build Time by Hour of Day ({col})")
        plt.xlabel("Hour of Day")
        plt.ylabel("Average Build Time (seconds)")
        plt.tight_layout()
        plt.show(block=False)

# 4. Summary statistics
def print_summary_stats(df, columns):
    print("Summary Statistics:")
    for col in columns:
        print(f"\n{col}:")
        print(df[col].describe())

# 5. Linear regression over time
def linear_regression_analysis(df, columns):
    for col in columns:
        df_non_na = df.dropna(subset=[col])
        slope, intercept, r_value, p_value, std_err = linregress(
            df_non_na["Timestamp"].map(pd.Timestamp.toordinal), df_non_na[col]
        )
        print(f"\nLinear Regression for {col}:")
        print(f"Slope: {slope:.2f} seconds/day")
        print(f"Intercept: {intercept:.2f}")
        print(f"R-squared: {r_value**2:.3f}")
        print(f"P-value: {p_value:.3f}")

# Run the analyses
plot_trends(df, build_columns)
analyze_day_of_week(df, build_columns)
analyze_time_of_day_lineplot(df, build_columns)
print_summary_stats(df, build_columns)
linear_regression_analysis(df, build_columns)
plt.show()
