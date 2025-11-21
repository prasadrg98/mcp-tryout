import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def visualize_vectors():
    """Visualize the vectors from your RAG application"""
    
    # Initialize the same embeddings and vectorstore from your RAG app
    print("🔄 Loading embeddings and vector store...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    vectorstore = Chroma(
        collection_name="educosys_genai_info", 
        embedding_function=embeddings, 
        persist_directory="./chroma_genai"
    )
    
    # Get all documents and their embeddings
    collection_data = vectorstore._collection.get(include=["embeddings", "documents", "metadatas"])
    
    print(f"📊 Found {len(collection_data['documents'])} documents in vector store")
    
    # Extract vectors and documents
    vectors = np.array(collection_data['embeddings'])
    documents = collection_data['documents']
    
    print(f"🎯 Vector dimensions: {vectors.shape}")
    print(f"📄 Sample document (first 100 chars): {documents[0][:100]}...")
    
    # 1. Basic Vector Statistics
    print("\n" + "="*50)
    print("📈 VECTOR STATISTICS")
    print("="*50)
    
    print(f"Vector shape: {vectors.shape}")
    print(f"Mean vector magnitude: {np.linalg.norm(vectors, axis=1).mean():.4f}")
    print(f"Min vector magnitude: {np.linalg.norm(vectors, axis=1).min():.4f}")
    print(f"Max vector magnitude: {np.linalg.norm(vectors, axis=1).max():.4f}")
    print(f"Vector dimension: {vectors.shape[1]}")
    
    # 2. Visualize first few dimensions
    plt.figure(figsize=(15, 5))
    
    plt.subplot(1, 3, 1)
    plt.hist(vectors[:, 0], bins=20, alpha=0.7, color='blue')
    plt.title('Distribution of 1st Dimension')
    plt.xlabel('Value')
    plt.ylabel('Frequency')
    
    plt.subplot(1, 3, 2)
    plt.hist(vectors[:, 1], bins=20, alpha=0.7, color='green')
    plt.title('Distribution of 2nd Dimension')
    plt.xlabel('Value')
    plt.ylabel('Frequency')
    
    plt.subplot(1, 3, 3)
    magnitudes = np.linalg.norm(vectors, axis=1)
    plt.hist(magnitudes, bins=20, alpha=0.7, color='red')
    plt.title('Vector Magnitudes Distribution')
    plt.xlabel('Magnitude')
    plt.ylabel('Frequency')
    
    plt.tight_layout()
    plt.savefig('vector_distributions.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 3. PCA Visualization (2D)
    print("\n🔍 Performing PCA dimensionality reduction...")
    pca = PCA(n_components=2)
    vectors_2d_pca = pca.fit_transform(vectors)
    
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.scatter(vectors_2d_pca[:, 0], vectors_2d_pca[:, 1], alpha=0.6, s=50)
    plt.title(f'PCA 2D Projection\n(Explained variance: {pca.explained_variance_ratio_.sum():.2%})')
    plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.2%} variance)')
    plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.2%} variance)')
    
    # Add some document labels for interesting points
    for i in range(min(5, len(documents))):
        plt.annotate(f'Doc {i}', 
                    (vectors_2d_pca[i, 0], vectors_2d_pca[i, 1]),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=8, alpha=0.7)
    
    # 4. t-SNE Visualization (2D)
    print("🔍 Performing t-SNE dimensionality reduction...")
    if len(vectors) > 2:  # t-SNE needs at least 3 points
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(vectors)-1))
        vectors_2d_tsne = tsne.fit_transform(vectors)
        
        plt.subplot(1, 2, 2)
        plt.scatter(vectors_2d_tsne[:, 0], vectors_2d_tsne[:, 1], alpha=0.6, s=50, color='orange')
        plt.title('t-SNE 2D Projection')
        plt.xlabel('t-SNE 1')
        plt.ylabel('t-SNE 2')
        
        # Add some document labels
        for i in range(min(5, len(documents))):
            plt.annotate(f'Doc {i}', 
                        (vectors_2d_tsne[i, 0], vectors_2d_tsne[i, 1]),
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=8, alpha=0.7)
    
    plt.tight_layout()
    plt.savefig('vector_projections.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 5. Similarity Heatmap
    print("\n🔥 Computing similarity heatmap...")
    if len(vectors) <= 20:  # Only for small datasets to avoid memory issues
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_matrix = cosine_similarity(vectors)
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(similarity_matrix, 
                   annot=True if len(vectors) <= 10 else False,
                   cmap='viridis', 
                   square=True,
                   fmt='.2f' if len(vectors) <= 10 else None)
        plt.title('Cosine Similarity Between Document Vectors')
        plt.xlabel('Document Index')
        plt.ylabel('Document Index')
        plt.savefig('similarity_heatmap.png', dpi=300, bbox_inches='tight')
        plt.show()
    else:
        print("⚠️  Too many documents for similarity heatmap. Showing first 20...")
        similarity_matrix = cosine_similarity(vectors[:20])
        plt.figure(figsize=(10, 8))
        sns.heatmap(similarity_matrix, annot=False, cmap='viridis', square=True)
        plt.title('Cosine Similarity Between First 20 Document Vectors')
        plt.savefig('similarity_heatmap_subset.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    # 6. Vector Component Analysis
    print("\n📊 Analyzing vector components...")
    
    # Find most active dimensions
    mean_abs_values = np.mean(np.abs(vectors), axis=0)
    top_dimensions = np.argsort(mean_abs_values)[-10:]  # Top 10 most active dimensions
    
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.bar(range(len(mean_abs_values[-20:])), mean_abs_values[-20:])
    plt.title('Mean Absolute Values - Top 20 Dimensions')
    plt.xlabel('Dimension Index (last 20)')
    plt.ylabel('Mean Absolute Value')
    
    plt.subplot(1, 2, 2)
    # Show variance across dimensions
    variances = np.var(vectors, axis=0)
    top_var_dims = np.argsort(variances)[-20:]
    plt.bar(range(20), variances[top_var_dims])
    plt.title('Variance - Top 20 Dimensions')
    plt.xlabel('Dimension Index (top variance)')
    plt.ylabel('Variance')
    
    plt.tight_layout()
    plt.savefig('vector_components.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 7. Document Content Analysis
    print("\n📚 DOCUMENT ANALYSIS")
    print("="*50)
    
    for i, doc in enumerate(documents[:3]):  # Show first 3 documents
        print(f"\n📄 Document {i}:")
        print(f"Length: {len(doc)} characters")
        print(f"Preview: {doc[:200]}...")
        print(f"Vector norm: {np.linalg.norm(vectors[i]):.4f}")
        print("-" * 30)
    
    return {
        'vectors': vectors,
        'documents': documents,
        'pca_2d': vectors_2d_pca if 'vectors_2d_pca' in locals() else None,
        'tsne_2d': vectors_2d_tsne if 'vectors_2d_tsne' in locals() else None,
        'similarity_matrix': similarity_matrix if 'similarity_matrix' in locals() else None
    }

if __name__ == "__main__":
    print("🚀 Starting vector visualization...")
    print("="*50)
    
    try:
        results = visualize_vectors()
        print("\n✅ Vector visualization complete!")
        print("📁 Generated files:")
        print("   - vector_distributions.png")
        print("   - vector_projections.png") 
        print("   - similarity_heatmap.png")
        print("   - vector_components.png")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have run the RAG app first to create the vector store!")
