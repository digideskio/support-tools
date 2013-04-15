// ==UserScript==
// @name       plot queries for mms
// @namespace  https://mms.10gen.com/
// @version    0.1
// @description  inspired by thomas rueckstiess' mplotqueries (https://github.com/rueckstiess/mtools) but for MMS
// @match      https://mms.10gen.com/host/detail/*
// @require    http://code.jquery.com/jquery-1.9.1.min.js
// @require    http://code.highcharts.com/highcharts.js
// @require    http://code.highcharts.com/modules/exporting.js
// @run-at     document-end
// @copyright  2013+, Stephen Lee
// ==/UserScript==
var renderScatterPlot = function() {
    var chart;
    
    var initializePlot = function( series ) {
        // FIXME might want to substitute highcharts for something like (http://www.flotcharts.org/)?
        var options = {
            chart: {
                type: 'scatter',
                zoomType: 'xy',
                renderTo: "plotqueries"
            },
            loading: {
                labelStyle: {
                    fontWeight: 'bold',
                    position: 'relative',
                    top: '1em'
                },
                style: {
                    position: 'absolute',
                    backgroundColor: 'white',
                    opacity: 0.5,
                    textAlign: 'center'
                }
            },
            title: {
                text: 'Database Profiler',
                align: "right"
            },
            exporting: {
                enabled: false // disabled since this is for internal use only
            },
            xAxis: {
                id: "datetime",
                title: {
                    enabled: true,
                    text: 'Time (GMT)'
                },
                startOnTick: true,
                endOnTick: true,
                showLastLabel: true,
                type: "datetime",
                dateTimeLabelFormats: {
                    hour: "%b %d<br/>%H:%M",
                    minute: "%b %d<br/>%H:%M",
                    second: "%b %d<br/>%H:%M:%S",
                    day: "%b %d"
                }
            },
            yAxis: {
                id: "millis",
                title: {
                    text: 'Operation Runtime [ms]'
                }
            },
            legend: {
                layout: 'vertical',
                align: 'left',
                verticalAlign: 'top',
                x: 0,
                y: 0,
                floating: false,
                backgroundColor: '#FFFFFF',
                borderWidth: 1,
                title: {
                    text: 'Legend: namespace (op)'
                }
            },
            plotOptions: {
                scatter: {
                    allowPointSelect: true,
                    point: {
                        events: {
                            select: function() {
                                if( this.operation === "insert" ) {
                                    return false;
                                }
                                
                                $( '#row' + this.index ).show();
                            },
                            unselect: function() {
                                $( '#row' + this.index ).hide();
                            },
                        }
                    },
                    marker: {
                        radius: 5,
                        states: {
                            hover: {
                                enabled: true,
                                lineColor: 'rgb(100,100,100)'
                            }
                        }
                    },
                    states: {
                        hover: {
                            marker: {
                                enabled: false
                            }
                        }
                    },
                    tooltip: {
                        headerFormat: '<b>{series.name}</b><br/>',
                        pointFormat: '{point.x}<br/>{point.millis} ms, {point.logms} log(ms)',
                        xDateFormat: '%Y-%m-%d %H:%M:%S'
                    }
                }
            },
            series: series
        };

        chart = new Highcharts.Chart( options );
    };
    
    var getAbsoluteSeries = function( scale ) {
        var hashedData = {};
        var series = [];
        var keys = [];
        
        $( "table#dbProfileTable tbody tr" ).each( function( index ) {
            var cols = $( this ).children( "td" );
            
            for( var i = 0; i < 4; i++ ) {
                if( cols[ i ] == null || cols[ i ].innerHTML.trim() == "" ) {
                    return true;
                }
            }
            
            // 0: datetime: "04-03-13 - 14:56:18"
            // 1: database: "gws2"
            // 2: ms: "5005"
            // 3: namespace: "gws2.log_postfix"
            // 4: operation: "update"
            var key = cols[ 3 ].innerHTML + ' (' + cols[ 4 ].innerHTML + ')';
            
            if( !( key in hashedData ) ) {
                keys.push( key );
                hashedData[ key ] = [];
            }
            
            datetime = cols[ 0 ].innerHTML;
            datetime = datetime.replace( " - ", " " );
            datetime = datetime.replace( '-', '/' );
            var absms = parseInt( cols[ 2 ].innerHTML );
            hashedData[ key ].push( { x: new Date( datetime ), 
                                      y: scale === "Logarithmic" ? Math.log( absms ) : absms,
                                      millis: absms,
                                      logms: Math.log( absms ),
                                      operation: cols[ 4 ].innerHTML,
                                      query: cols[ 5 ].innerHTML,
                                      update: cols[ 6 ].innerHTML,
                                      index: index,
                                      namespace: cols[ 3 ].innerHTML
                                    } );
            
            var str = '<div id="row' + index + '" style="display: none; padding: 5px"><p><b>query</b>:' + 
                                      cols[ 5 ].innerHTML + '</p>';
            
            if( cols[ 4 ].innerHTML === "update" ) {
                str += '<p><b>update</b>:' + cols[ 6 ].innerHTML + '</p>';
            }
            
            str += "</div>";
            $( "#plotqueries" ).after( str );
        } );
        
        keys = keys.sort();
        
        for( var i = 0; i < keys.length; i++ ) {
            series.push( { name : keys[ i ], data : hashedData[ keys[ i ] ], xAxis : "datetime", yAxis : "millis" } );
        }
        
        return( series );
    };
    
    $( "#hostProfileData" ).siblings().hide();
    $( "#hostProfileData" ).hide();
    $( "#hostProfileData" ).before( '<div id="plotqueries" style="min-width: 400px; height: 500px; margin: 0 auto; padding: 5px"></div>' );
    $( "#plotqueries" ).before( '<div>Y-Axis: <select id="scale"><option value="absolute">Absolute</option><option value="logarithmic">Logarithmic</option></select></div>' );
    $( "table#dbProfileTable" ).ready( function() {
        initializePlot( getAbsoluteSeries( "Absolute" ) );
    } );
    $( "#scale" ).change( function( event ) {
        var isLog = $( "#scale option:selected" ).text() === "Logarithmic";
        chart.showLoading( "Changing scale to " + $( "#scale option:selected" ).text() );
        chart.yAxis[ 0 ].update( { type : isLog ? "logarithmic" : "linear" }, true );
        
        if( isLog ) {
            chart.yAxis[ 0 ].update( { title : { text : "Operation Runtime [log(ms)]" } }, true );
        } else {
            chart.yAxis[ 0 ].update( { title : { text : "Operation Runtime [ms]" } }, true );
        }

        chart.hideLoading();
    } );
};

if( window.location.href.indexOf( "https://mms.10gen.com/host/detail/profileData/" ) == 0 ) {
    if( $( '#profileData table tr' ).length < 1 ) {
        alert( "No profiling data, so going back!" );
        window.history.back();
    }
    
    renderScatterPlot();
} else {
    // FIXME ugly hack to get the customerId
    var customerId = $('#navHosts a').attr( "href" );
    
    if( customerId.indexOf( "/host/list/" ) == 0 ) {
        customerId = customerId.replace( "/host/list/", "" );
    }
  
    // FIXME more ugly hacks to redirect to actual data page
    $('a[data-tabname="hostProfileDataTab"]').click( function( event ) {
        window.location.href = event.target.href;
    } );
}