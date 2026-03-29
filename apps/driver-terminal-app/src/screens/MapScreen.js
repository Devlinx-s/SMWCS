import React from 'react'
import { View, Text, ScrollView, StyleSheet } from 'react-native'
import { useRouteStore } from '../store/useStore'
import { COLORS } from '../config'

// Full map requires react-native-maps which needs bare workflow
// This screen shows a coordinate list as a map alternative for Expo Go
export default function MapScreen() {
  const route = useRouteStore(s => s.route)
  const stops = route?.stops || []

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Route Map</Text>
        <Text style={styles.sub}>
          {stops.length} stops in this route
        </Text>
      </View>

      <View style={styles.mapPlaceholder}>
        <Text style={styles.mapIcon}>🗺️</Text>
        <Text style={styles.mapText}>Route Overview</Text>
        <Text style={styles.mapSub}>
          Full map available in production build
        </Text>
      </View>

      <ScrollView style={styles.list}>
        {stops.map((stop, i) => (
          <View key={i} style={[styles.item,
            stop.completed && styles.itemDone]}>
            <View style={styles.itemDot}>
              <Text style={styles.itemNum}>
                {stop.completed ? '✓' : stop.stop_order}
              </Text>
            </View>
            <View style={{flex:1}}>
              <Text style={styles.itemId}>{stop.sensor_id || stop.bin_id}</Text>
              <Text style={styles.itemCoords}>
                {stop.lat && stop.lon
                  ? `${stop.lat.toFixed(5)}, ${stop.lon.toFixed(5)}`
                  : 'GPS coordinates pending'}
              </Text>
              {stop.fill_pct != null && (
                <Text style={[styles.itemFill,
                  {color: stop.fill_pct >= 90 ? COLORS.red :
                          stop.fill_pct >= 70 ? COLORS.amber : COLORS.green}]}>
                  Fill: {stop.fill_pct.toFixed(1)}%
                </Text>
              )}
            </View>
            <View style={[styles.statusDot,
              {backgroundColor: stop.completed ? COLORS.green :
                                i === 0 ? COLORS.teal : COLORS.gray_dark}]} />
          </View>
        ))}
        {stops.length === 0 && (
          <Text style={styles.empty}>No stops in current route</Text>
        )}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container:      { flex:1, backgroundColor:COLORS.bg },
  header:         { backgroundColor:COLORS.surface, padding:16, paddingTop:48 },
  title:          { fontSize:18, fontWeight:'bold', color:COLORS.white },
  sub:            { fontSize:12, color:COLORS.gray, marginTop:2 },
  mapPlaceholder: { height:180, backgroundColor:COLORS.surface2,
                    margin:12, borderRadius:12,
                    justifyContent:'center', alignItems:'center' },
  mapIcon:        { fontSize:40, marginBottom:8 },
  mapText:        { fontSize:16, fontWeight:'bold', color:COLORS.white },
  mapSub:         { fontSize:12, color:COLORS.gray, marginTop:4 },
  list:           { flex:1, padding:12 },
  item:           { flexDirection:'row', alignItems:'center',
                    backgroundColor:COLORS.surface, borderRadius:10,
                    padding:12, marginBottom:8 },
  itemDone:       { opacity:0.5 },
  itemDot:        { width:32, height:32, borderRadius:16,
                    backgroundColor:COLORS.teal,
                    justifyContent:'center', alignItems:'center',
                    marginRight:12 },
  itemNum:        { color:COLORS.white, fontWeight:'bold', fontSize:13 },
  itemId:         { fontSize:13, fontWeight:'600', color:COLORS.white },
  itemCoords:     { fontSize:11, color:COLORS.gray, marginTop:2 },
  itemFill:       { fontSize:12, marginTop:2 },
  statusDot:      { width:10, height:10, borderRadius:5, marginLeft:8 },
  empty:          { textAlign:'center', color:COLORS.gray,
                    marginTop:40, fontSize:14 },
})
