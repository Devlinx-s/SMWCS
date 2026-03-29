import React from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createStackNavigator } from '@react-navigation/stack'
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs'
import { Text } from 'react-native'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import { SafeAreaProvider } from 'react-native-safe-area-context'

import LoginScreen   from './src/screens/LoginScreen'
import HomeScreen    from './src/screens/HomeScreen'
import MapScreen     from './src/screens/MapScreen'
import StatusScreen  from './src/screens/StatusScreen'
import ProfileScreen from './src/screens/ProfileScreen'
import { COLORS }    from './src/config'

const Stack = createStackNavigator()
const Tab   = createBottomTabNavigator()

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown:             false,
        tabBarStyle:             { backgroundColor: COLORS.surface,
                                   borderTopColor: COLORS.surface2,
                                   paddingBottom: 4 },
        tabBarActiveTintColor:   COLORS.teal,
        tabBarInactiveTintColor: COLORS.gray,
      }}
    >
      <Tab.Screen
        name="Route"
        component={HomeScreen}
        options={{
          tabBarLabel: 'Route',
          tabBarIcon: ({ color }) =>
            <Text style={{ color, fontSize: 20 }}>🗑️</Text>
        }}
      />
      <Tab.Screen
        name="Map"
        component={MapScreen}
        options={{
          tabBarLabel: 'Map',
          tabBarIcon: ({ color }) =>
            <Text style={{ color, fontSize: 20 }}>🗺️</Text>
        }}
      />
      <Tab.Screen
        name="Status"
        component={StatusScreen}
        options={{
          tabBarLabel: 'Status',
          tabBarIcon: ({ color }) =>
            <Text style={{ color, fontSize: 20 }}>📡</Text>
        }}
      />
    </Tab.Navigator>
  )
}

function MainStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Tabs"    component={MainTabs} />
      <Stack.Screen name="Profile" component={ProfileScreen} />
    </Stack.Navigator>
  )
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <NavigationContainer>
          <Stack.Navigator screenOptions={{ headerShown: false }}>
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="Main"  component={MainStack} />
          </Stack.Navigator>
        </NavigationContainer>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  )
}
