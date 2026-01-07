document.addEventListener('DOMContentLoaded', function() {

    const chartDom = document.getElementById('chart');
    const fanListDom = document.getElementById('fan-list');
    const projectSelectDom = document.getElementById('project-select');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const descriptionContainer = document.getElementById('description-container');

    const myChart = echarts.init(chartDom);

    // 检测是否为移动设备
    function isMobile() {
        return window.innerWidth <= 768;
    }

    // 获取响应式配置
    function getResponsiveConfig() {
        const mobile = isMobile();
        return {
            grid: {
                right: mobile ? '15%' : '25%',
                left: mobile ? '15%' : '10%',
                bottom: mobile ? '15%' : '10%',
                top: mobile ? '15%' : '10%'
            },
            xAxis: {
                nameLocation: 'middle',
                nameGap: mobile ? 35 : 25,
                nameTextStyle: {
                    fontSize: mobile ? 12 : 14,
                    fontWeight: 'bold'
                },
                axisLabel: {
                    fontSize: mobile ? 10 : 12
                }
            },
            yAxis: {
                nameLocation: 'middle',
                nameGap: mobile ? 50 : 45,
                nameTextStyle: {
                    fontSize: mobile ? 12 : 14,
                    fontWeight: 'bold'
                },
                axisLabel: {
                    fontSize: mobile ? 10 : 12,
                    formatter: function (value) {
                        return value.toFixed(2);
                    }
                }
            },
            legend: {
                orient: 'vertical',
                right: mobile ? '2%' : '2%',
                top: 'center',
                width: mobile ? '12%' : '20%',
                textStyle: {
                    fontSize: mobile ? 9 : 11
                },
                type: 'scroll',
                pageIconSize: mobile ? 10 : 12,
                pageTextStyle: {
                    fontSize: mobile ? 8 : 10
                }
            },
            title: {
                textStyle: {
                    fontSize: mobile ? 14 : 18
                }
            }
        };
    }

    // 预定义的基础颜色池（去除重复）
    const baseColors = [
        '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
        '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#d14a61',
        '#6e7074', '#546570', '#c4ccd3', '#e59696', '#b6d7a8',
        '#ffd966', '#a4c2f4', '#d5a6bd', '#9fc5e8', '#ead1dc',
        '#f4cccc', '#fce5cd', '#fff2cc', '#d9ead3', '#d0e0e3',
        '#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#6ab04c',
        '#badc58', '#f0932b', '#eb4d4b', '#c44569', '#574b90',
        '#f8b500', '#00d2d3', '#1e3799', '#b71540', '#079992',
        '#38ada9', '#78e08f', '#fa983a', '#e55039', '#4a69bd',
        '#60a3bc', '#e58e26', '#f53b57', '#3c40c6', '#0fbcf9',
        '#ffa801', '#05c46b', '#ffd32a', '#ff3f34', '#00d8d6'
    ];

    // 动态生成颜色的函数（当基础颜色不够时使用）
    function generateColor(index) {
        if (index < baseColors.length) {
            return baseColors[index];
        }
        
        // 使用HSL颜色空间生成不重复的颜色
        // 通过改变色相(Hue)来生成不同颜色
        const hue = (index * 137.508) % 360; // 使用黄金角度分布
        const saturation = 65 + (index % 3) * 10; // 65-85%
        const lightness = 50 + (index % 4) * 5; // 50-65%
        
        return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
    }

    // 生成足够多的颜色（支持最多100个不同的颜色）
    const colors = Array.from({ length: 100 }, (_, i) => generateColor(i));

    const option = {
        color: colors,
        title: {
            text: '', // Title will be set dynamically
            left: 'center'
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            },
            formatter: function (params) {
                if (!params || params.length === 0) return;
                
                // 获取所有选中点的噪声值（应该都是相同的）
                const noise = params[0].value[0];
                let result = '噪声: ' + noise + ' dBA<br/>';
                
                // 为每个数据点添加温度和转速信息
                params.forEach(function (item) {
                    const temp = item.value[1];
                    const speed = item.value[2];
                    result += item.marker + ' ' + item.seriesName + ' : ' + temp + ' ℃';
                    if (speed !== undefined) {
                        result += ' (转速: ' + speed + ' RPM)';
                    }
                    result += '<br/>';
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
            right: '25%',
            containLabel: false
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
            {
                type: 'inside',
                filterMode: 'none'  // 不过滤数据，确保所有点都参与连线
            },
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

        // 获取响应式配置
        const responsiveConfig = getResponsiveConfig();
        
        // Update chart title and axes with responsive config
        myChart.setOption({
            title: { 
                text: project.title,
                ...responsiveConfig.title
            },
            xAxis: { 
                name: project.xAxisName,
                ...responsiveConfig.xAxis
            },
            yAxis: { 
                name: project.yAxisName,
                ...responsiveConfig.yAxis
            },
            grid: responsiveConfig.grid,
            legend: responsiveConfig.legend
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

    // 从URL路径加载项目
    function loadProjectFromPath() {
        const path = window.location.pathname;
        if (path && path !== '/') {
            // 移除开头的斜杠
            const projectName = decodeURIComponent(path.substring(1));
            const project = projects.find(p => p.name === projectName);
            if (project) {
                projectSelectDom.value = project.name;
                loadProjectData(project);
                return true;
            }
        }
        return false;
    }

    // 更新URL路径
    function updatePath(projectName) {
        const newPath = '/' + encodeURIComponent(projectName);
        window.history.pushState({ project: projectName }, '', newPath);
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
                        updatePath(selectedProjectName);
                        loadProjectData(selectedProject);
                    }
                });

                // 监听浏览器前进/后退按钮
                window.addEventListener('popstate', () => {
                    loadProjectFromPath();
                });

                // 页面加载时尝试从URL加载项目，如果没有则加载第一个
                if (!loadProjectFromPath()) {
                    updatePath(projects[0].name);
                    loadProjectData(projects[0]);
                }
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

            return {
                name: fanName,
                type: 'line',
                smooth: false,  // 改为false以避免平滑曲线在边界处的问题
                symbol: 'circle',
                symbolSize: 6,
                clip: false,
                connectNulls: true,  // 连接空值点
                data: originalData,
                itemStyle: {
                    color: colors[index % colors.length]
                },
                lineStyle: {
                    color: colors[index % colors.length]
                },
                emphasis: {           // 添加hover效果
                    focus: 'series',  // 高亮当前系列
                    blurScope: 'coordinateSystem',  // 只在同一坐标系内模糊
                    scale: 1.5        // 放大数据点
                },
                blur: {               // 自定义模糊效果
                    lineStyle: {
                        opacity: 0.2  // 未高亮曲线的透明度（0.3比默认的0.05更清晰）
                    },
                    itemStyle: {
                        opacity: 0.2  // 未高亮数据点的透明度
                    }
                }
            };
        });

        // 获取响应式配置
        const responsiveConfig = getResponsiveConfig();

        myChart.setOption({
            legend: {
                data: selectedFans,
                ...responsiveConfig.legend
            },
            series: newSeries
        }, {
            replaceMerge: 'series'
        });
    }


    window.addEventListener('resize', function() {
        myChart.resize();
        
        // 在窗口大小改变时更新响应式配置
        if (currentProject) {
            const responsiveConfig = getResponsiveConfig();
            myChart.setOption({
                title: responsiveConfig.title,
                xAxis: responsiveConfig.xAxis,
                yAxis: responsiveConfig.yAxis,
                grid: responsiveConfig.grid,
                legend: responsiveConfig.legend
            });
        }
    });
});
