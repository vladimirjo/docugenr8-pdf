#!/bin/bash

# Read version from version.txt file and remove non-numerical characters
version=$(sed 's/[^0-9.]//g' version.txt)

# Package name
package_name="docugenr8-pdf"

# Fetch package versions from Test PyPI
versions=$(curl -sSL https://test.pypi.org/simple/${package_name}/ | grep -o '<a [^>]*>.*</a>' | sed -e 's/<[^>]*>//g')

# Check if version exists
if echo "$versions" | grep -q "$version"; then
    echo "Version $version exists on Test PyPI"
    exit -1
else
    echo "Version $version does not exist on Test PyPI"
    exit 0
fi
