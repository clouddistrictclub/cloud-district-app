import { View, Text, StyleSheet, TouchableOpacity, Image, Platform } from 'react-native';
import { memo } from 'react';
import { useRouter } from 'expo-router';

interface Product {
  id: string;
  name: string;
  brand: string;
  image: string;
  puffCount: number;
  flavor: string;
  price: number;
  stock: number;
}

const ProductCard = memo(({ product }: { product: Product }) => {
  const router = useRouter();

  const imgSource = product.image ? { uri: product.image } : undefined;

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => router.push(`/product/${product.id}`)}
      activeOpacity={0.85}
      data-testid={`product-card-${product.id}`}
    >
      <View style={styles.imageWrap}>
        {imgSource ? (
          Platform.OS === 'web' ? (
            <img
              src={product.image}
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              loading="lazy"
              alt={product.name}
              data-testid={`product-img-${product.id}`}
            />
          ) : (
            <Image source={imgSource} style={styles.image} resizeMode="cover" testID={`product-img-${product.id}`} />
          )
        ) : (
          <View style={styles.imagePlaceholder}>
            <Text style={styles.placeholderText}>No Image</Text>
          </View>
        )}
        {product.stock === 0 && (
          <View style={styles.outOfStockBadge}>
            <Text style={styles.outOfStockText}>Sold Out</Text>
          </View>
        )}
      </View>
      <View style={styles.info}>
        <Text style={styles.brand}>{product.brand}</Text>
        <Text style={styles.name} numberOfLines={1}>{product.name}</Text>
        <Text style={styles.flavor} numberOfLines={1}>{product.flavor}</Text>
        <View style={styles.footer}>
          <Text style={styles.price} data-testid={`product-price-${product.id}`}>${product.price.toFixed(2)}</Text>
          <View style={styles.puffPill}>
            <Text style={styles.puffText}>{product.puffCount.toLocaleString()} puffs</Text>
          </View>
        </View>
      </View>
    </TouchableOpacity>
  );
});

ProductCard.displayName = 'ProductCard';

export default ProductCard;

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: '#141414',
    borderRadius: 14,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#1e1e1e',
  },
  imageWrap: {
    width: '100%',
    aspectRatio: 4 / 3,
    backgroundColor: '#1a1a1a',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  imagePlaceholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderText: {
    color: '#444',
    fontSize: 12,
  },
  outOfStockBadge: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: 'rgba(220,38,38,0.85)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  outOfStockText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  info: {
    padding: 10,
    gap: 2,
  },
  brand: {
    fontSize: 11,
    color: '#2E6BFF',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  name: {
    fontSize: 14,
    color: '#fff',
    fontWeight: '600',
  },
  flavor: {
    fontSize: 12,
    color: '#777',
    marginBottom: 6,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  price: {
    fontSize: 17,
    color: '#fff',
    fontWeight: '800',
  },
  puffPill: {
    backgroundColor: '#1e1e1e',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  puffText: {
    fontSize: 10,
    color: '#888',
    fontWeight: '600',
  },
});
