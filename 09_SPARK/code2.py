from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StringIndexer, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml import Pipeline
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
from pyspark.sql.functions import avg, count, col

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("Adult Dataset Clustering") \
    .getOrCreate()

# Define the schema for the dataset
schema = StructType([
    StructField("age", IntegerType(), True),
    StructField("workclass", StringType(), True),
    StructField("fnlwgt", IntegerType(), True),
    StructField("education", StringType(), True),
    StructField("education_num", IntegerType(), True),
    StructField("marital_status", StringType(), True),
    StructField("occupation", StringType(), True),
    StructField("relationship", StringType(), True),
    StructField("race", StringType(), True),
    StructField("sex", StringType(), True),
    StructField("capital_gain", IntegerType(), True),
    StructField("capital_loss", IntegerType(), True),
    StructField("hours_per_week", IntegerType(), True),
    StructField("native_country", StringType(), True),
    StructField("income", StringType(), True)
])

# Read the data
data = spark.read.csv("adult.data", schema=schema)

# Select the features we want to cluster on (age, workclass, education)
selected_features = ["age", "workclass", "education"]
data_subset = data.select(selected_features)

# Convert categorical variables to numeric using StringIndexer
workclass_indexer = StringIndexer(inputCol="workclass", outputCol="workclass_index")
education_indexer = StringIndexer(inputCol="education", outputCol="education_index")

# Combine features into a vector
assembler = VectorAssembler(
    inputCols=["age", "workclass_index", "education_index"],
    outputCol="features"
)

# Scale the features
scaler = StandardScaler(
    inputCol="features",
    outputCol="scaled_features",
    withStd=True,
    withMean=True
)

# Create K-means model
kmeans = KMeans(k=3, featuresCol="scaled_features", predictionCol="cluster", seed=42)

# Create and fit the pipeline
pipeline = Pipeline(stages=[
    workclass_indexer,
    education_indexer,
    assembler,
    scaler,
    kmeans
])

# Fit the pipeline and transform the data
model = pipeline.fit(data_subset)
clustered_data = model.transform(data_subset)

# Show the results with better formatting
print("\nClustering Results:")
clustered_data.select(
    "age", 
    "workclass", 
    "education", 
    "cluster"
).show(20, truncate=False)

# Get cluster centers
kmeans_model = model.stages[-1]
centers = kmeans_model.clusterCenters()
print("\nCluster Centers (scaled features):")
for i, center in enumerate(centers):
    print(f"Cluster {i}: {center}")

# Calculate cluster statistics using proper Column syntax
print("\nCluster Statistics:")
cluster_stats = clustered_data.groupBy("cluster").agg(
    avg("age").alias("avg_age"),
    count("workclass").alias("count"),
    count(col("education")).alias("education_count")
)
cluster_stats.show()

# Show detailed distribution of education levels in each cluster
print("\nEducation Distribution by Cluster:")
clustered_data.groupBy("cluster", "education").count().orderBy("cluster", "education").show(30, truncate=False)

# Show detailed distribution of workclass in each cluster
print("\nWorkclass Distribution by Cluster:")
clustered_data.groupBy("cluster", "workclass").count().orderBy("cluster", "workclass").show(30, truncate=False)

# Calculate age statistics for each cluster
print("\nAge Statistics by Cluster:")
clustered_data.groupBy("cluster").agg(
    avg("age").alias("avg_age"),
    count("age").alias("count")
).orderBy("cluster").show()

# # Before spark.stop(), add these analyses:

# print("\n1. Country with highest number of adults (excluding USA):")
# country_counts = data.filter(col("native_country") != "United-States") \
#     .groupBy("native_country") \
#     .count() \
#     .orderBy(col("count").desc())
# country_counts.show(1)

# print("\n2. Number of people with Masters or higher education in Tech-support:")
# masters_tech = data.filter(
#     (col("education").isin(["Masters", "Doctorate"])) & 
#     (col("occupation") == "Tech-support")
# ).count()
# print(f"Number of people with Masters/Doctorate in Tech-support: {masters_tech}")

# print("\n3. Number of unmarried males in Local-govt:")
# unmarried_local_govt = data.filter(
#     (col("sex") == "Male") & 
#     (col("workclass") == "Local-gov") &
#     (col("marital_status").isin(["Never-married", "Divorced", "Separated", "Widowed"]))
# ).count()
# print(f"Number of unmarried males in Local-govt: {unmarried_local_govt}")
# # Before spark.stop(), replace the previous analyses with these:

print("\n1. Country with highest number of adults (excluding USA):")
country_counts = data.filter(
    (col("native_country") != "United-States") & 
    (col("native_country").isNotNull()) & 
    (col("native_country") != " United-States") &  # Handle possible space variants
    (col("native_country") != "?")  # Remove unknown values
).groupBy("native_country") \
    .count() \
    .orderBy(col("count").desc())
country_counts.show(5)  # Show top 5 to verify results

print("\n2. Number of people with Masters or higher education in Tech-support:")
# First, let's see what values actually exist in our data
print("Unique occupations:")
data.select("occupation").distinct().show(truncate=False)
print("\nUnique education levels:")
data.select("education").distinct().show(truncate=False)

masters_tech = data.filter(
    (col("education").isin(["Masters", "Doctorate", " Masters", " Doctorate"])) & 
    (col("occupation").isin(["Tech-support", " Tech-support"]))
).count()
print(f"Number of people with Masters/Doctorate in Tech-support: {masters_tech}")

print("\n3. Number of unmarried males in Local-govt:")
unmarried_local_govt = data.filter(
    (col("sex").contains("Male")) & 
    (col("workclass").contains("Local-gov")) &
    (
        col("marital_status").contains("Never-married") |
        col("marital_status").contains("Divorced") |
        col("marital_status").contains("Separated") |
        col("marital_status").contains("Widowed")
    )
).count()
print(f"Number of unmarried males in Local-govt: {unmarried_local_govt}")


# Now stop the Spark session
spark.stop()