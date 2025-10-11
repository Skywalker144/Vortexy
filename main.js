document.addEventListener('DOMContentLoaded', function() {

    const chartDom = document.getElementById('chart');
    const fanListDom = document.getElementById('fan-list');
    const projectSelectDom = document.getElementById('project-select');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const descriptionContainer = document.getElementById('description-container');

    const myChart = echarts.init(chartDom);

    // 定义更多的颜色，避免颜色重复
    const colors = [
        '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
        '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#d14a61',
        '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
        '#6e7074', '#546570', '#c4ccd3', '#e59696', '#b6d7a8',
        '#ffd966', '#a4c2f4', '#d5a6bd', '#9fc5e8', '#ead1dc',
        '#f4cccc', '#fce5cd', '#fff2cc', '#d9ead3', '#d0e0e3'
    ];

    const option = {
        color: colors,
        title: {
            text: '', // Title will be set dynamically
            left: 'center'
        },
        tooltip: {
            trigger: 'axis',
            formatter: function (params) {
                if (!params.length) return;
                const yAxisName = myChart.getOption().yAxis[0].name;
                const yAxisUnit = yAxisName.includes('℃') ? '℃' : (yAxisName.includes('%') ? '%' : '');
                let result = '噪声: ' + params[0].axisValueLabel + ' dBA<br/>';
                params.forEach(function (item) {
                    result += item.marker + ' ' + item.seriesName + ' : ' + item.value[1] + ' ' + yAxisUnit + '<br/>';
                });
                return result;
            }
        },

        legend: {
            // data: [],
            orient: 'vertical',
            right: '2%',
            top: 'center',
            width: '20%',
            textStyle: {
                fontSize: 11
            },
            type: 'scroll',
            pageIconSize: 12,
            pageTextStyle: {
                fontSize: 10
            }
        },

        grid: {
            right: '25%'
        },

        xAxis: {
            name: '噪声 (dBA)',
            type: 'value',
            scale: true,
            nameLocation: 'middle',
            nameGap: 25
        },

        yAxis: {
            name: '温度 (℃)',
            type: 'value',
            scale: true,
            nameLocation: 'middle',
            nameGap: 45,
            axisLabel: {
                formatter: function (value) {
                    return value.toFixed(2);
                }
            }
        },

        dataZoom: [
            { type: 'inside' },
//            { type: 'slider' }
        ],

        series: []
    };

    myChart.setOption(option);

    let allFanData = {};
    let projects = [];
    let currentProject = null;

    function loadProjectData(project) {
        currentProject = project;
        // Clear previous data
        allFanData = {};
        fanListDom.innerHTML = '';
        selectAllCheckbox.checked = false;
        descriptionContainer.innerHTML = '';
        myChart.setOption({ series: [] });

        // Update chart title and axes
        myChart.setOption({
            title: { text: project.title },
            xAxis: { name: project.xAxisName },
            yAxis: { name: project.yAxisName }
        });

        // Update description
        if (project.description) {
            descriptionContainer.innerHTML = project.description;
        }

        fetch(project.dataFile)
            .then(response => response.json())
            .then(data => {
                allFanData = data;
                const fanNames = Object.keys(data);

                fanNames.forEach(name => {
                    const label = document.createElement('label');
                    const checkbox = document.createElement('input');

                    checkbox.type = 'checkbox';
                    checkbox.value = name;
                    checkbox.addEventListener('change', () => {
                        updateSelectAllState();
                        updateChart();
                    });

                    label.appendChild(checkbox);
                    label.appendChild(document.createTextNode(' ' + name));
                    fanListDom.appendChild(label);
                });
            })
            .catch(error => {
                console.error(`加载 ${project.dataFile} 文件失败:`, error);
                fanListDom.innerHTML = `<p style='color: red;'>加载项目数据失败，请检查 ${project.dataFile} 文件。</p>`;
            });
    }

    fetch('projects.json')
        .then(response => response.json())
        .then(data => {
            projects = data;
            if (projects.length > 0) {
                projects.forEach(proj => {
                    const option = document.createElement('option');
                    option.value = proj.name;
                    option.textContent = proj.name;
                    projectSelectDom.appendChild(option);
                });
                projectSelectDom.addEventListener('change', (e) => {
                    const selectedProjectName = e.target.value;
                    const selectedProject = projects.find(p => p.name === selectedProjectName);
                    if (selectedProject) {
                        loadProjectData(selectedProject);
                    }
                });
                // Load the first project by default
                loadProjectData(projects[0]);
            } else {
                 fanListDom.innerHTML = "<p style='color: red;'>未找到任何项目，请检查projects.json文件。</p>";
            }
        })
        .catch(error => {
            console.error("加载projects.json文件失败:", error);
            fanListDom.innerHTML = "<p style='color: red;'>加载项目配置失败，请检查projects.json文件是否存在。</p>";
        });

    selectAllCheckbox.addEventListener('change', () => {
        const fanCheckboxes = fanListDom.querySelectorAll('input[type="checkbox"]');
        fanCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
        });
        updateChart();
    });

    function updateSelectAllState() {
        const fanCheckboxes = fanListDom.querySelectorAll('input[type="checkbox"]');
        const allChecked = [...fanCheckboxes].every(checkbox => checkbox.checked);
        const noneChecked = [...fanCheckboxes].every(checkbox => !checkbox.checked);

        if (allChecked) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else if (noneChecked) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else {
            selectAllCheckbox.indeterminate = true;
        }
    }

    function updateChart() {
        const selectedFans = [];
        document.querySelectorAll('#fan-list input[type="checkbox"]:checked').forEach(checkbox => {
            selectedFans.push(checkbox.value);
        });

        const newSeries = selectedFans.map((fanName, index) => {

            const originalData = allFanData[fanName];

            const swappedData = originalData.map(point => [point[1], point[0]]);

            return {
                name: fanName,
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                clip: false,
                data: swappedData,
                itemStyle: {
                    color: colors[index % colors.length]
                },
                lineStyle: {
                    color: colors[index % colors.length]
                }
            };
        });

        myChart.setOption({
            legend: {
                data: selectedFans
            },
            series: newSeries
        }, {
            replaceMerge: 'series'
        });
    }


    window.addEventListener('resize', function() {
        myChart.resize();
    });
});
