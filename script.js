let originalData = null;
let cleanedData = null;

// File input handling
document.getElementById('fileInput').addEventListener('change', handleFileSelect);

// Clean data button handling
document.getElementById('cleanData').addEventListener('click', handleDataCleaning);

// Download button handling
document.getElementById('downloadData').addEventListener('click', handleDownload);

async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    document.getElementById('fileName').textContent = file.name;
    document.getElementById('cleanData').disabled = false;
    
    try {
        const text = await file.text();
        originalData = parseCSV(text);
        displayPreview(originalData, 'Original Data');
    } catch (error) {
        showStatus('Error reading file: ' + error.message, 'error');
    }
}

function parseCSV(text) {
    const lines = text.trim().split('\n');
    const headers = lines[0].split(',').map(header => header.trim());
    
    const data = lines.slice(1).map(line => {
        const values = line.split(',').map(value => value.trim());
        return headers.reduce((obj, header, index) => {
            obj[header] = values[index];
            return obj;
        }, {});
    });

    return { headers, data };
}

function handleDataCleaning() {
    if (!originalData) return;

    cleanedData = JSON.parse(JSON.stringify(originalData));
    const options = getSelectedOptions();

    if (options.dropDuplicates) {
        cleanedData.data = dropDuplicates(cleanedData.data);
    }

    if (options.handleMissing) {
        cleanedData = handleMissingValues(cleanedData);
    }

    if (options.convertTypes) {
        cleanedData = convertDataTypes(cleanedData);
    }

    if (options.standardizeColumns) {
        cleanedData = standardizeColumnNames(cleanedData);
    }

    if (options.removeOutliers) {
        cleanedData = removeOutliers(cleanedData);
    }

    displayPreview(cleanedData, 'Cleaned Data');
    document.getElementById('downloadData').disabled = false;
    showStatus('Data cleaning completed successfully!', 'success');
}

function getSelectedOptions() {
    return {
        dropDuplicates: document.getElementById('dropDuplicates').checked,
        handleMissing: document.getElementById('handleMissing').checked,
        convertTypes: document.getElementById('convertTypes').checked,
        standardizeColumns: document.getElementById('standardizeColumns').checked,
        removeOutliers: document.getElementById('removeOutliers').checked
    };
}

function dropDuplicates(data) {
    const seen = new Set();
    return data.filter(row => {
        const key = JSON.stringify(row);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

function handleMissingValues(dataset) {
    const { headers, data } = dataset;
    
    // Calculate means and modes for each column
    const columnStats = headers.reduce((stats, header) => {
        const values = data.map(row => row[header]).filter(val => val !== '' && val != null);
        const isNumeric = values.every(val => !isNaN(val));
        
        if (isNumeric) {
            stats[header] = {
                type: 'numeric',
                mean: values.reduce((sum, val) => sum + parseFloat(val), 0) / values.length
            };
        } else {
            const frequencies = values.reduce((freq, val) => {
                freq[val] = (freq[val] || 0) + 1;
                return freq;
            }, {});
            const mode = Object.entries(frequencies)
                .sort((a, b) => b[1] - a[1])[0]?.[0] || '';
            stats[header] = { type: 'categorical', mode };
        }
        return stats;
    }, {});

    // Fill missing values
    const cleanedData = data.map(row => {
        const newRow = { ...row };
        headers.forEach(header => {
            if (newRow[header] === '' || newRow[header] == null) {
                const stats = columnStats[header];
                newRow[header] = stats.type === 'numeric' ? stats.mean : stats.mode;
            }
        });
        return newRow;
    });

    return { headers, data: cleanedData };
}

function convertDataTypes(dataset) {
    const { headers, data } = dataset;
    
    // Detect and convert date columns
    const datePattern = /^\d{4}-\d{2}-\d{2}|\d{2}\/\d{2}\/\d{4}$/;
    
    const cleanedData = data.map(row => {
        const newRow = { ...row };
        headers.forEach(header => {
            const value = newRow[header];
            if (typeof value === 'string') {
                if (datePattern.test(value)) {
                    newRow[header] = new Date(value).toISOString().split('T')[0];
                } else if (!isNaN(value)) {
                    newRow[header] = parseFloat(value);
                }
            }
        });
        return newRow;
    });

    return { headers, data: cleanedData };
}

function standardizeColumnNames(dataset) {
    const { headers, data } = dataset;
    
    const standardizedHeaders = headers.map(header => 
        header.toLowerCase().replace(/\s+/g, '_')
    );

    const cleanedData = data.map(row => {
        return headers.reduce((newRow, oldHeader, index) => {
            newRow[standardizedHeaders[index]] = row[oldHeader];
            return newRow;
        }, {});
    });

    return { headers: standardizedHeaders, data: cleanedData };
}

function removeOutliers(dataset) {
    const { headers, data } = dataset;
    
    // Only remove outliers from numeric columns
    const numericColumns = headers.filter(header => 
        data.every(row => !isNaN(row[header]))
    );

    const stats = numericColumns.reduce((acc, header) => {
        const values = data.map(row => parseFloat(row[header]));
        const sorted = values.sort((a, b) => a - b);
        const q1 = sorted[Math.floor(sorted.length * 0.25)];
        const q3 = sorted[Math.floor(sorted.length * 0.75)];
        const iqr = q3 - q1;
        acc[header] = {
            lowerBound: q1 - 1.5 * iqr,
            upperBound: q3 + 1.5 * iqr
        };
        return acc;
    }, {});

    const cleanedData = data.filter(row => {
        return numericColumns.every(header => {
            const value = parseFloat(row[header]);
            const { lowerBound, upperBound } = stats[header];
            return value >= lowerBound && value <= upperBound;
        });
    });

    return { headers, data: cleanedData };
}

function displayPreview(dataset, title) {
    const { headers, data } = dataset;
    const previewData = data.slice(0, 5);
    
    let html = `<h3>${title}</h3>`;
    html += '<table><thead><tr>';
    headers.forEach(header => {
        html += `<th>${header}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    previewData.forEach(row => {
        html += '<tr>';
        headers.forEach(header => {
            html += `<td>${row[header]}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    document.getElementById('previewTable').innerHTML = html;
}

function handleDownload() {
    if (!cleanedData) return;

    const csv = [
        cleanedData.headers.join(','),
        ...cleanedData.data.map(row => 
            cleanedData.headers.map(header => row[header]).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'cleaned_data.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function showStatus(message, type) {
    const statusElement = document.getElementById('status');
    statusElement.textContent = message;
    statusElement.className = `status ${type}`;
}