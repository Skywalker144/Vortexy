document.addEventListener('DOMContentLoaded', function() {

    const chartDom = document.getElementById('chart');
    const fanListDom = document.getElementById('fan-list');
    const projectSelectDom = document.getElementById('project-select');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const descriptionContainer = document.getElementById('description-container');

    const myChart = echarts.init(chartDom);

    const option = {
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

            min: function (value) {
                const span = value.max - value.min;
                return value.min - span * 0.1;
            },

            max: function (value) {
                const span = value.max - value.min;
                return value.max + span * 0.1;
            },
            nameLocation: 'middle',
            nameGap: 25
        },

        yAxis: {
            name: '温度 (℃)',
            type: 'value',
            min: function (value) {
                const span = value.max - value.min;
                return value.min - span * 0.1;
            },

            max: function (value) {
                const span = value.max - value.min;
                return value.max + span * 0.1;
            },
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

        const newSeries = selectedFans.map(fanName => {

            const originalData = allFanData[fanName];

            const swappedData = originalData.map(point => [point[1], point[0]]);

            return {
                name: fanName,
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                data: swappedData
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
