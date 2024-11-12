#!/bin/bash

# Define installation paths
rm -rf output
HADOOP_VERSION="3.4.0" 
JAVA_VERSION="17.0.12"
HADOOP_HOME="$HOME/hadoop-$HADOOP_VERSION"
JAVA_HOME="$HOME/jdk-$JAVA_VERSION"

# Check and download Hadoop if not already installed
if [ ! -d "$HADOOP_HOME" ]; then
   echo "Downloading Hadoop $HADOOP_VERSION..."
   wget -q --show-progress "https://dlcdn.apache.org/hadoop/common/hadoop-$HADOOP_VERSION/hadoop-$HADOOP_VERSION.tar.gz" -O hadoop.tar.gz
   echo "Extracting Hadoop..."
   tar -xzf hadoop.tar.gz -C $HOME
   rm hadoop.tar.gz
fi

# Check and download Java if not already installed
if [ ! -d "$JAVA_HOME" ]; then
   echo "Downloading Java $JAVA_VERSION..."
   wget -q --show-progress "https://download.oracle.com/java/17/archive/jdk-17.0.12_linux-x64_bin.tar.gz" -O jdk.tar.gz
   echo "Extracting Java..."
   tar -xzf jdk.tar.gz -C $HOME
   rm jdk.tar.gz
fi

export JAVA_HOME="$HOME/jdk-$JAVA_VERSION"

# Set environment variables for Hadoop and Java
export PATH=$PATH:$HADOOP_HOME/bin:$JAVA_HOME/bin
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export HADOOP_COMMON_HOME=$HADOOP_HOME
export HADOOP_HDFS_HOME=$HADOOP_HOME
export HADOOP_MAPRED_HOME=$HADOOP_HOME
export HADOOP_YARN_HOME=$HADOOP_HOME
export HADOOP_LOG_DIR=$HADOOP_HOME/logs

# Create HDFS input directory if it doesn't exist
hdfs dfs -test -d input || hdfs dfs -mkdir -p input

# Upload files to HDFS input directory if they aren't already there
for FILE in "big.txt" "iris.txt"; do
    if ! hdfs dfs -test -e "input/$FILE"; then
        echo "Uploading $FILE to HDFS..."
        hdfs dfs -put $FILE input/
    else
        echo "$FILE already exists in HDFS input directory."
    fi
done

# Get the list of mapper, reducer, and combiner files
mappers=($(ls -1 mapper*.py))
reducers=($(ls -1 reducer*.py))
combiners=($(ls -1 combiner*.py))

# Display the options for the user
echo "Available mapper files:"
for i in "${!mappers[@]}"; do
    echo "$i. ${mappers[$i]}"
done

read -p "Enter the index of the mapper file: " mapper_index

echo "Available reducer files:"
for i in "${!reducers[@]}"; do
    echo "$i. ${reducers[$i]}"
done

read -p "Enter the index of the reducer file: " reducer_index

echo "Available combiner files:"
for i in "${!combiners[@]}"; do
    echo "$i. ${combiners[$i]}"
done

read -p "Enter the index of the combiner file (leave blank if none): " combiner_index

# Get the selected file names
MAPPER=${mappers[$mapper_index]}
REDUCER=${reducers[$reducer_index]}
if [ -n "$combiner_index" ]; then
    COMBINER=${combiners[$combiner_index]}
else
    COMBINER=""
fi

# Prompt for input file
read -p "Enter input file (big.txt or iris.txt): " FILEINPUT

# Run Hadoop Streaming job
echo "Running Hadoop Streaming job..."

if [ -n "$COMBINER" ]; then
    hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
        -input input/$FILEINPUT \
        -output output \ 
        -mapper "$(which python3) $MAPPER" \
        -reducer "$(which python3) $REDUCER" \
        -combiner "$(which python3) $COMBINER"
else
    hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
        -input input/$FILEINPUT \
        -output output \
        -mapper "$(which python3) $MAPPER" \
        -reducer "$(which python3) $REDUCER"
fi
